from django.db import migrations


FORWARD = '''
CREATE FUNCTION finance_budget_category_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE owner_id bigint; category_kind varchar;
BEGIN
 IF NEW.category_id IS NOT NULL THEN
  SELECT user_id, kind INTO owner_id, category_kind FROM finance_category
   WHERE id=NEW.category_id FOR UPDATE;
  IF NOT FOUND OR owner_id<>NEW.user_id OR category_kind<>'expense' THEN
   RAISE EXCEPTION 'budget_category_owner_or_kind' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER budget_category_guard BEFORE INSERT OR UPDATE ON finance_budget
 FOR EACH ROW EXECUTE FUNCTION finance_budget_category_guard();
CREATE FUNCTION finance_category_budget_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM finance_budget WHERE category_id=OLD.id
  AND (user_id<>NEW.user_id OR NEW.kind<>'expense')) THEN
  RAISE EXCEPTION 'category_has_budgets' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER category_budget_guard BEFORE UPDATE OF kind,user_id ON finance_category
 FOR EACH ROW EXECUTE FUNCTION finance_category_budget_guard();
'''
REVERSE = '''
DROP TRIGGER IF EXISTS category_budget_guard ON finance_category;
DROP FUNCTION IF EXISTS finance_category_budget_guard();
DROP TRIGGER IF EXISTS budget_category_guard ON finance_budget;
DROP FUNCTION IF EXISTS finance_budget_category_guard();
'''


def apply_guards(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(FORWARD, params=None)


def remove_guards(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(REVERSE, params=None)


class Migration(migrations.Migration):
    dependencies = [('finance', '0008_budget_category_guards')]
    operations = [migrations.RunPython(apply_guards, remove_guards)]
