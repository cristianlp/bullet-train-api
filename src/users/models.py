from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import get_template

from app.utils import create_hash
from organisations.models import Organisation


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class FFAdminUser(AbstractUser):

    organisations = models.ManyToManyField(Organisation, related_name="users", blank=True)
    email = models.EmailField(unique=True, null=False)
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['id']

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Invite(models.Model):
    email = models.EmailField()
    hash = models.CharField(max_length=100, default=create_hash, unique=True)
    date_created = models.DateTimeField('DateCreated', auto_now_add=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    frontend_base_url = models.CharField(max_length=500, null=False)

    class Meta:
        unique_together = ('email', 'organisation')

    def get_invite_uri(self):
        return self.frontend_base_url + str(self.hash)

    def save(self, *args, **kwargs):
        # send email invite before saving invite
        self.send_invite_mail()
        super(Invite, self).save(*args, **kwargs)

    def send_invite_mail(self):
        context = {
            "org_name": self.organisation.name,
            "invite_url": self.get_invite_uri()
        }

        html_template = get_template('users/invite_to_org.html')
        plaintext_template = get_template('users/invite_to_org.txt')

        subject = 'You have been invited to join an organisation on Bullet Train'
        from_email = 'noreply@bullettrain.com'
        to = self.email

        text_content = plaintext_template.render(context)
        html_content = html_template.render(context)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    def __str__(self):
        return "%s %s" % (self.email, self.organisation.name)

    def __unicode__(self):
        return "%s %s" % (self.email, self.organisation.name)
