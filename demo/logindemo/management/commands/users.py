from django.core.management.base import BaseCommand
from logindemo.models import MyUser

class Command(BaseCommand):
    help = 'Add or delete a user'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['add', 'delete'], help='Action to perform')
        parser.add_argument('email', help='email of the user to add or delete')

    def handle(self, *args, **options):
        action = options['action']
        email = options['email']

        if action == 'add':
            # Prompt the user for additional information
            #email = input('Email: ')
            first_name = input('First name: ')
            last_name = input('Last name: ')
            password = input('Password: ')

            # Create the user
            user = MyUser.objects.create_user(email=email, password=password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully added user {email}'))
        elif action == 'delete':
            try:
                # Retrieve the user
                user = MyUser.objects.get(email=email)

                # Delete the user
                user.delete()

                self.stdout.write(self.style.SUCCESS(f'Successfully deleted user {email}'))
            except MyUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {email} does not exist'))