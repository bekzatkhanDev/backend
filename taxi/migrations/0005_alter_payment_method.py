from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0004_tripsharetoken_tripchatroom_chatmessage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('cash', 'Cash'),
                    ('card', 'Card'),
                    ('kaspi', 'Kaspi Bank'),
                    ('halyk', 'Halyk Bank'),
                    ('freedom', 'Freedom Bank'),
                ],
            ),
        ),
    ]
