"""Protocol tests only: no fit, predictions, refit or writes to sealed runs."""
import unittest

from scripts import run_vietnamese_classification_experiment as experiment


class VietnameseProtocolTests(unittest.TestCase):
    def setUp(self):
        self.cfg=experiment.read(experiment.CONFIG)

    def test_normalization_keeps_vietnamese_accents_and_nfc(self):
        value=experiment.normalize_description('  ĐO\u0301NG\t HỌC  PHÍ ')
        self.assertEqual(value,'đóng học phí')
        self.assertNotEqual(value,'dong hoc phi')

    def test_exact_tie_chooses_smaller_C_then_word(self):
        candidates=[{'id':'dummy','family':'dummy','C':None,'macro_f1':1.0},
                    {'id':'char-large','family':'char_linearsvc','C':10,'macro_f1':0.8},
                    {'id':'char-small','family':'char_linearsvc','C':0.1,'macro_f1':0.8},
                    {'id':'word-small','family':'word_logreg','C':0.1,'macro_f1':0.8}]
        self.assertEqual(experiment.select(candidates,self.cfg)['id'],'word-small')

    def test_primary_macro_f1_is_not_rounded_to_create_ties(self):
        candidates=[{'id':'word','family':'word_logreg','C':0.1,'macro_f1':0.8611070878},
                    {'id':'char','family':'char_linearsvc','C':10,'macro_f1':0.8611248229}]
        self.assertEqual(experiment.select(candidates,self.cfg)['id'],'char')

    def test_pipeline_feature_settings_and_no_accent_stripping(self):
        for family,expected in [('word_logreg',('word',(1,2))),('char_linearsvc',('char_wb',(3,5)))]:
            model=experiment.pipeline(family,1,self.cfg)
            self.assertEqual(list(model.named_steps),['tfidf','classifier'])
            vector=model.named_steps['tfidf']
            self.assertEqual((vector.analyzer,vector.ngram_range),expected)
            self.assertEqual(vector.min_df,1)
            self.assertFalse(vector.lowercase)
            self.assertIsNone(vector.strip_accents)
            self.assertFalse(hasattr(vector,'vocabulary_'))

    def test_sealed_data_counts_groups_and_ambiguous_exclusion(self):
        parts,ambiguous=experiment.verify_source(self.cfg)
        self.assertEqual({s:len(rows) for s,rows in parts.items()},{'train':464,'validation':99,'test':99})
        self.assertEqual({s:len({r['group_id'] for r in rows}) for s,rows in parts.items()},
                         {'train':406,'validation':87,'test':90})
        self.assertEqual(len(ambiguous),48)
        self.assertTrue(all(r['label'] is None and r['split']=='excluded' for r in ambiguous))

    def test_completed_run_rejects_retraining_and_second_test_pass(self):
        run=experiment.RUN_BASE/'task10b-vi-v1'
        with self.assertRaisesRegex(ValueError,'Training already started/completed'):
            experiment.train(run)
        with self.assertRaisesRegex(ValueError,'Test already started'):
            experiment.evaluate(run)


if __name__=='__main__':unittest.main()
