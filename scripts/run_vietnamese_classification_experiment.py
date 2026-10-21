"""TASK 10B: verify sealed Vietnamese data -> lock protocol -> train -> select -> test.

No website writes, English training data, refit, split search or threshold fitting.
All models, row-level outputs and run receipts stay in ignored data/experiments/.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finance.classification import normalize_description
from finance.classification_labels import LABELS

SOURCE = ROOT/'data/vietnamese/classification/vi-authored-v1'
CONFIG = ROOT/'experiments/vietnamese-classification-v1.json'
RUN_BASE = ROOT/'data/experiments/classification-vietnamese'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def event(run, name, **fields):
    with (run/'events.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps({'at_utc':now(),'event':name,**fields}, ensure_ascii=False)+'\n')


def runtime():
    from importlib.metadata import version
    return {'python':platform.python_version(), **{p:version(p) for p in
            ['scikit-learn','numpy','scipy','joblib','threadpoolctl']}}


def verify_source(cfg):
    for name, key in [('dataset.jsonl','dataset_sha256'),('split-manifest.json','split_sha256'),
                      ('manifest.json','dataset_manifest_sha256'),('split-lock.json','dataset_lock_sha256')]:
        if sha(SOURCE/name) != cfg[key]:
            raise ValueError('Pinned source hash differs: '+name)
    lock = read(SOURCE/'split-lock.json')
    for name, expected in {**lock['source_sha256'],**lock['locked_output_sha256']}.items():
        if sha(SOURCE/name) != expected:
            raise ValueError('Dataset lock mismatch: '+name)
    for name, expected in lock['external_code_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Normalization or label source changed: '+name)
    for name, meta in read(SOURCE/'manifest.json')['files'].items():
        if sha(SOURCE/name)!=meta['sha256'] or (SOURCE/name).stat().st_size!=meta['bytes']:
            raise ValueError('Dataset manifest mismatch: '+name)
    rows = [json.loads(line) for line in (SOURCE/'dataset.jsonl').read_text(encoding='utf-8').splitlines()]
    by_id = {r['id']:r for r in rows}
    if len(by_id)!=len(rows) or set(r['label'] for r in rows)!=set(LABELS):
        raise ValueError('IDs or labels invalid')
    partitions = {s:[r for r in rows if r['split']==s] for s in cfg['samples']}
    for split, part in partitions.items():
        if len(part)!=cfg['samples'][split] or len({r['group_id'] for r in part})!=cfg['groups'][split]:
            raise ValueError('Pinned sample/group counts differ: '+split)
        if set(r['label'] for r in part)!=set(LABELS):
            raise ValueError('Label absent from split')
    split_manifest = read(SOURCE/'split-manifest.json')
    if len(split_manifest['records'])!=len(rows):
        raise ValueError('Manifest row count mismatch')
    for r in split_manifest['records']:
        actual=by_id[r['id']]
        if any(actual[k]!=r[k] for k in ['id','scenario_id','group_id','split']):
            raise ValueError('Manifest membership mismatch')
    expected_groups=defaultdict(list)
    for r in rows:
        expected_groups[r['group_id']].append(r['id'])
        if r['variant_of']:
            parent=by_id[r['variant_of']]
            if any(r[k]!=parent[k] for k in ['label','scenario_id','group_id','split']):
                raise ValueError('Variant relationship crosses group/split')
    if set(expected_groups)!=set(split_manifest['groups']):
        raise ValueError('Group manifest IDs differ')
    for g, members in expected_groups.items():
        if sorted(members)!=sorted(split_manifest['groups'][g]['members']):
            raise ValueError('Group members differ')
    spec=importlib.util.spec_from_file_location('vi_data_audit',SOURCE/'build_and_audit.py')
    audit_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit_module)
    for field in ['group_id','scenario_id']:
        mapping=defaultdict(set)
        for r in rows:mapping[r[field]].add(r['split'])
        if any(len(v)!=1 for v in mapping.values()):raise ValueError('Relationship overlap')
    for key in [lambda x:x,normalize_description,audit_module.fold,audit_module.diagnostic_key]:
        mapping=defaultdict(set)
        for r in rows:mapping[key(r['description'])].add(r['split'])
        if any(len(v)!=1 for v in mapping.values()):raise ValueError('Text key overlap')
    near=read(SOURCE/'near-pairs.json')
    if len(near['weak_cross_split_candidates'])!=cfg['weak_cross_split_warnings']:
        raise ValueError('Known weak-warning count differs')
    for edge in near['strong_edges_grouped_before_split']:
        if by_id[edge['a']]['split']!=by_id[edge['b']]['split']:
            raise ValueError('Strong near edge crosses split')
    ambiguous=[json.loads(line) for line in (SOURCE/'ambiguous.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(ambiguous)!=cfg['ambiguous_excluded'] or any(r['label'] is not None or r['split']!='excluded' or r['id'] in by_id for r in ambiguous):
        raise ValueError('Ambiguous rows entered supervised data')
    return partitions, ambiguous


def verify_protocol(run):
    protocol=read(run/'protocol.json')
    if sha(run/'protocol.json')!=(run/'protocol.sha256').read_text().strip():
        raise ValueError('Protocol receipt differs')
    for name, expected in protocol['source_hashes'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Experiment source changed: '+name)
    if runtime()!=protocol['runtime']:raise ValueError('Runtime differs from locked protocol')
    verify_source(protocol['config'])
    return protocol


def prepare(run):
    if run.exists():raise ValueError('Use a new run directory; existing runs are never replaced')
    cfg=read(CONFIG)
    if cfg['C_values']!=[0.1,1,10] or cfg['input_fields']!=['description'] or cfg['refit_train_validation']:
        raise ValueError('Unsupported statistical design')
    parts, ambiguous=verify_source(cfg)
    paths=[CONFIG,Path(__file__),ROOT/'finance/classification.py',ROOT/'finance/classification_labels.py',
           ROOT/'scripts/run_classification_windows.py']
    # Lock references every dataset source/output already sealed in TASK 10A.
    paths += [p for p in SOURCE.iterdir() if p.is_file() and p.name in
              ['manifest.json','split-lock.json','dataset.jsonl','split-manifest.json','ambiguous.jsonl','near-pairs.json']]
    run.mkdir(parents=True)
    save(run/'config.json',cfg)
    save(run/'protocol.json',{'locked_before_first_fit_at_utc':now(),'config':cfg,'runtime':runtime(),
        'source_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        'partition_id_hashes':{s:hashlib.sha256('\n'.join(r['id'] for r in part).encode()).hexdigest() for s,part in parts.items()},
        'labels':list(LABELS),'structural_test_read_only':True,'test_predictions_before_selection':False,
        'warnings':'24 weak cross-split similarities, same AI author, no independent human review; synthetic only'})
    (run/'protocol.sha256').write_text(sha(run/'protocol.json')+'\n',encoding='utf-8')
    event(run,'protocol_locked_before_first_fit',protocol_sha256=sha(run/'protocol.json'))
    print(json.dumps({'locked':True,'protocol_sha256':sha(run/'protocol.json'),
                     'samples':{s:len(v) for s,v in parts.items()},'ambiguous':len(ambiguous)},indent=2))


def pipeline(family, c, cfg):
    from sklearn.pipeline import Pipeline
    from sklearn.dummy import DummyClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    if family=='dummy':return Pipeline([('classifier',DummyClassifier(**cfg['dummy'],random_state=cfg['seed']))])
    vector_cfg=dict(cfg['word_tfidf'] if family=='word_logreg' else cfg['char_tfidf'])
    vector_cfg['ngram_range']=tuple(vector_cfg['ngram_range'])
    classifier=(LogisticRegression(C=c,random_state=cfg['seed'],**cfg['logreg']) if family=='word_logreg'
                else LinearSVC(C=c,random_state=cfg['seed'],**cfg['linearsvc']))
    return Pipeline([('tfidf',TfidfVectorizer(**vector_cfg)),('classifier',classifier)])


def select(candidates, cfg):
    eligible=[r for r in candidates if r['family']!='dummy']
    return min(eligible,key=lambda r:(-r['macro_f1'],r['C'],cfg['family_order'].index(r['family'])))


def vectors_zero(model, text):
    if 'tfidf' not in model.named_steps:return None
    return int((model.named_steps['tfidf'].transform(text).getnnz(axis=1)==0).sum())


def runtime_context(run):
    # Existing adapter only changes this offline process, never package files/server.
    import threadpoolctl
    from run_classification_windows import install_adapter
    description=install_adapter()
    receipt={'recorded_at_utc':now(),'adapter':description,'threadpoolctl_source_sha256':sha(threadpoolctl.__file__),
             'adapter_source_sha256':sha(ROOT/'scripts/run_classification_windows.py'),
             'installed_packages_modified':False}
    return threadpoolctl, receipt


def train(run):
    import joblib
    from sklearn.metrics import accuracy_score,f1_score
    protocol=verify_protocol(run);cfg=protocol['config'];parts,_=verify_source(cfg)
    if (run/'models').exists() or (run/'selection.json').exists() or (run/'results.json').exists():
        raise ValueError('Training already started/completed; never retrain after test')
    train_rows,val_rows=parts['train'],parts['validation']
    x=[normalize_description(r['description']) for r in train_rows];y=[r['label'] for r in train_rows]
    xv=[normalize_description(r['description']) for r in val_rows];yv=[r['label'] for r in val_rows]
    threadpoolctl,receipt=runtime_context(run)
    with threadpoolctl.threadpool_limits(limits=cfg['thread_limit']):
        receipt['threadpools']=[{'internal_api':p['internal_api'],'num_threads':p['num_threads']} for p in threadpoolctl.threadpool_info()]
        if any(p['num_threads']!=cfg['thread_limit'] for p in receipt['threadpools']):raise ValueError('Thread limit ineffective')
        save(run/'runtime-before-first-fit.json',receipt)
        (run/'models').mkdir()
        candidates=[]
        for family,c in [('dummy',None)]+[(f,c) for f in cfg['family_order'] for c in cfg['C_values']]:
            candidate_id=family if c is None else f'{family}_C_{str(c).replace(".","p")}'
            model=pipeline(family,c,cfg)
            event(run,'fit_start',candidate=candidate_id,fit_split='train',samples=len(x))
            start=time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always');model.fit(x,y)
            elapsed=time.perf_counter()-start
            predicted=model.predict(xv)
            path=run/'models'/f'{candidate_id}.joblib';joblib.dump(model,path)
            score={'id':candidate_id,'family':family,'C':c,'accuracy':float(accuracy_score(yv,predicted)),
                   'macro_f1':float(f1_score(yv,predicted,labels=protocol['labels'],average='macro',zero_division=0)),
                   'validation_zero_vectors':vectors_zero(model,xv),'fit_seconds':elapsed,
                   'fit_rows':len(x),'vocabulary_size':len(model.named_steps['tfidf'].vocabulary_) if 'tfidf' in model.named_steps else None,
                   'warnings':[type(w.message).__name__+': '+str(w.message) for w in caught],
                   'model_sha256':sha(path)}
            candidates.append(score)
            event(run,'validation_complete',candidate=candidate_id,macro_f1=score['macro_f1'])
        save(run/'validation.json',{'candidates':candidates,'labels':protocol['labels']})
        chosen=select(candidates,cfg)
        save(run/'selection.json',{'selected_id':chosen['id'],'selected_model_sha256':chosen['model_sha256'],
             'validation_macro_f1':chosen['macro_f1'],'selected_at_utc':now(),'rule':cfg['selection'],
             'validation_sha256':sha(run/'validation.json'),'protocol_sha256':sha(run/'protocol.json'),
             'refit_train_validation':False})
        (run/'selection.sha256').write_text(sha(run/'selection.json')+'\n',encoding='utf-8')
        event(run,'selection_locked_before_test',selected_id=chosen['id'],selection_sha256=sha(run/'selection.json'))
    print(json.dumps({'selected':chosen,'validation':candidates},ensure_ascii=False,indent=2))


def load_selected(run):
    protocol=verify_protocol(run);selection=read(run/'selection.json')
    if sha(run/'selection.json')!=(run/'selection.sha256').read_text().strip():raise ValueError('Selection lock differs')
    if sha(run/'validation.json')!=selection['validation_sha256'] or sha(run/'protocol.json')!=selection['protocol_sha256']:
        raise ValueError('Validation or protocol changed after selection')
    candidates=read(run/'validation.json')['candidates']
    if select(candidates,protocol['config'])['id']!=selection['selected_id']:raise ValueError('Selection rule mismatch')
    if selection['refit_train_validation']:raise ValueError('Unexpected refit')
    return protocol,selection,{c['id']:c for c in candidates}


def evaluate(run):
    import joblib
    from sklearn.metrics import accuracy_score,classification_report,confusion_matrix,f1_score
    protocol,selection,candidates=load_selected(run);cfg=protocol['config'];parts,ambiguous=verify_source(cfg)
    if (run/'test-start.json').exists():raise ValueError('Test already started; no repeated evaluation or tuning')
    # Create irreversible receipt before the first test prediction.
    save(run/'test-start.json',{'at_utc':now(),'selection_sha256':sha(run/'selection.json'),
                             'models':['dummy',selection['selected_id']]})
    event(run,'final_test_start',models=['dummy',selection['selected_id']])
    text=[normalize_description(r['description']) for r in parts['test']];truth=[r['label'] for r in parts['test']]
    threadpoolctl,_=runtime_context(run)
    results={};predictions={};selected_model=None
    with threadpoolctl.threadpool_limits(limits=cfg['thread_limit']):
        for name in ['dummy',selection['selected_id']]:
            path=run/'models'/f'{name}.joblib'
            if sha(path)!=candidates[name]['model_sha256']:raise ValueError('Model changed since train fit')
            model=joblib.load(path)
            if name==selection['selected_id']:
                if sha(path)!=selection['selected_model_sha256']:raise ValueError('Selected artifact differs')
                selected_model=model
            predicted=model.predict(text);predictions[name]=list(map(str,predicted))
            results[name]={'accuracy':float(accuracy_score(truth,predicted)),
              'macro_f1':float(f1_score(truth,predicted,labels=protocol['labels'],average='macro',zero_division=0)),
              'classification_report':classification_report(truth,predicted,labels=protocol['labels'],output_dict=True,zero_division=0),
              'confusion_matrix':confusion_matrix(truth,predicted,labels=protocol['labels']).tolist(),
              'errors':sum(a!=b for a,b in zip(truth,predicted)), 'test_samples':len(truth),
              'test_zero_vectors':vectors_zero(model,text),'validation_zero_vectors':candidates[name]['validation_zero_vectors'],
              'fit_seconds':candidates[name]['fit_seconds'],'model_sha256':sha(path)}
            event(run,'final_test_model_complete',candidate=name)
        save(run/'test-predictions.json',{'records':[{'id':r['id'],'group_id':r['group_id'],
                'description':r['description'],'true':r['label'],
                'predictions':{name:values[i] for name,values in predictions.items()}} for i,r in enumerate(parts['test'])]})
        errors=[{'id':r['id'],'description':r['description'],'true':r['label'],
                 'predicted':predictions[selection['selected_id']][i]} for i,r in enumerate(parts['test'])
                 if r['label']!=predictions[selection['selected_id']][i]]
        save(run/'test-errors.json',{'errors':errors,'test_modified':False})
        event(run,'ambiguous_predictions_after_selection_and_test',samples=len(ambiguous))
        ax=[normalize_description(r['description']) for r in ambiguous]
        ap=selected_model.predict(ax)
        matrix=selected_model.named_steps['tfidf'].transform(ax)
        save(run/'ambiguous-predictions.json',{'no_accuracy_or_f1':True,'no_rejection_threshold':True,
             'records':[{'id':r['id'],'description':r['description'],'predicted':str(ap[i]),
                        'zero_vector':bool(matrix.getrow(i).nnz==0),'gold_label':None,
                        'exclusion_type':r['exclusion_type']} for i,r in enumerate(ambiguous)]})
    output={'evaluated_at_utc':now(),'selected_id':selection['selected_id'],'labels':protocol['labels'],
        'protocol_sha256':sha(run/'protocol.json'),'selection_sha256':sha(run/'selection.json'),
        'dataset_sha256':cfg['dataset_sha256'],'split_sha256':cfg['split_sha256'],'runtime':protocol['runtime'],
        'models':results,'ambiguous':{'samples':len(ambiguous),'predicted_counts':dict(Counter(map(str,ap))),
                    'zero_vectors':int((matrix.getnnz(axis=1)==0).sum()),'metrics':None,'threshold_selected':False},
        'known_weak_warnings':24,'independent_human_review':False,'real_user_generalization_claimed':False,
        'refit_train_validation':False}
    save(run/'results.json',output)
    (run/'results.sha256').write_text(sha(run/'results.json')+'\n',encoding='utf-8')
    event(run,'evaluation_complete',results_sha256=sha(run/'results.json'))
    print(json.dumps({'selected_id':selection['selected_id'],'test':{k:{n:v for n,v in m.items() if n not in ['classification_report','confusion_matrix']} for k,m in results.items()},'ambiguous':output['ambiguous']},ensure_ascii=False,indent=2))


def verify(run):
    protocol,selection,candidates=load_selected(run)
    if sha(run/'results.json')!=(run/'results.sha256').read_text().strip():raise ValueError('Results changed')
    for c in candidates.values():
        if sha(run/'models'/f'{c["id"]}.joblib')!=c['model_sha256']:raise ValueError('Model changed')
    result=read(run/'results.json')
    if set(result['models'])!={'dummy',selection['selected_id']}:raise ValueError('Other models evaluated on test')
    if result['selection_sha256']!=sha(run/'selection.json'):raise ValueError('Results selection mismatch')
    events=[json.loads(l) for l in (run/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    names=[e['event'] for e in events]
    if not names.index('protocol_locked_before_first_fit')<names.index('fit_start')<names.index('selection_locked_before_test')<names.index('final_test_start')<names.index('ambiguous_predictions_after_selection_and_test'):
        raise ValueError('Phase chronology invalid')
    print(json.dumps({'verified':True,'selected':selection['selected_id'],'test_models':list(result['models']),
                     'fit_count':sum(n=='fit_start' for n in names),'test_unchanged':True,'refit':False},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','train','evaluate','verify'])
    parser.add_argument('--run-dir',default='data/experiments/classification-vietnamese/task10b-vi-v1')
    args=parser.parse_args();run=(ROOT/args.run_dir).resolve()
    if not run.is_relative_to(RUN_BASE.resolve()) or run==RUN_BASE.resolve():parser.error('Run must be inside ignored Vietnamese experiment directory')
    {'prepare':prepare,'train':train,'evaluate':evaluate,'verify':verify}[args.phase](run)


if __name__=='__main__':main()
