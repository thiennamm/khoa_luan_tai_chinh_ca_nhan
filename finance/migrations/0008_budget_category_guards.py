from django.db import migrations


# SQLite CHECK không tham chiếu được bảng khác. Trigger giữ quan hệ chủ/loại
# ngay cả khi bulk_create/update bỏ qua model.clean(). Không sửa bản ghi cũ.
FORWARD = '''
CREATE TRIGGER budget_category_insert_guard BEFORE INSERT ON finance_budget
WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM finance_category c WHERE c.id=NEW.category_id
 AND c.user_id=NEW.user_id AND c.kind='expense')
BEGIN SELECT RAISE(ABORT, 'budget_category_owner_or_kind'); END;
CREATE TRIGGER budget_category_update_guard BEFORE UPDATE ON finance_budget
WHEN NEW.category_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM finance_category c WHERE c.id=NEW.category_id
 AND c.user_id=NEW.user_id AND c.kind='expense')
BEGIN SELECT RAISE(ABORT, 'budget_category_owner_or_kind'); END;
CREATE TRIGGER category_budget_update_guard BEFORE UPDATE OF kind,user_id ON finance_category
WHEN EXISTS (SELECT 1 FROM finance_budget b WHERE b.category_id=OLD.id
 AND (b.user_id<>NEW.user_id OR NEW.kind<>'expense'))
BEGIN SELECT RAISE(ABORT, 'category_has_budgets'); END;
'''
REVERSE = '''
DROP TRIGGER IF EXISTS category_budget_update_guard;
DROP TRIGGER IF EXISTS budget_category_update_guard;
DROP TRIGGER IF EXISTS budget_category_insert_guard;
'''


def apply_sqlite_guards(apps, schema_editor):
    if schema_editor.connection.vendor == 'sqlite':
        for statement in schema_editor.connection.ops.prepare_sql_script(FORWARD):
            schema_editor.execute(statement)


def remove_sqlite_guards(apps, schema_editor):
    if schema_editor.connection.vendor == 'sqlite':
        for statement in schema_editor.connection.ops.prepare_sql_script(REVERSE):
            schema_editor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [('finance', '0007_budget')]
    # SQLite đã áp dụng 0008 không chạy lại. Cài mới PostgreSQL bỏ qua cú pháp
    # SQLite ở đây và nhận trigger tương ứng từ 0009. SQL SQLite giữ nguyên.
    operations = [migrations.RunPython(apply_sqlite_guards, remove_sqlite_guards)]
