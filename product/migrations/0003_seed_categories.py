from django.db import migrations


def seed_categories(apps, schema_editor):
    Category = apps.get_model('product', 'Category')

    categories = [
        {
            'name': 'AI',
            'slug': 'ai',
            'description': 'AI tools, artificial intelligence services, and subscriptions.',
        },
        {
            'name': 'Tools',
            'slug': 'tools',
            'description': 'Productivity, developer, design, and utility tools subscriptions.',
        },
        {
            'name': 'Streaming Platform',
            'slug': 'streaming-platform',
            'description': 'Video, music, and digital media streaming platforms subscriptions.',
        },
    ]

    for cat in categories:
        obj, created = Category.objects.get_or_create(
            name=cat['name'],
            defaults={
                'slug': cat['slug'],
                'description': cat['description']
            }
        )
        if not created and not obj.slug:
            obj.slug = cat['slug']
            obj.save(update_fields=['slug'])


def rollback_categories(apps, schema_editor):
    Category = apps.get_model('product', 'Category')
    Category.objects.filter(name__in=['Tools', 'Streaming Platform']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0002_productplan_devices_alter_productplan_currency_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_code=rollback_categories),
    ]
