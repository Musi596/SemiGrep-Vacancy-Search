from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models

# Create your models here.

class Vacancy(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.FileField(
        upload_to="vacancies/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"])],
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        permissions = [("manage_vacancies", "Can manage all vacancies")]  # noqa: RUF012


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.FileField(
        upload_to="avatars/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"])],
    )

    def __str__(self):
        return f"Профиль {self.user.username}"


class FavoriteVacancy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_vacancies")
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "vacancy"), name="unique_user_favorite_vacancy"),
        ]
        ordering = ("-created_at",)


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    class Messenger(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"

    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE)
    applicant_full_name = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.CharField(max_length=32, blank=True, null=True)
    messenger = models.CharField(max_length=10, choices=Messenger.choices, blank=True, null=True)
    messenger_contact = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        permissions = [("manage_applications", "Can manage all applications")]  # noqa: RUF012
