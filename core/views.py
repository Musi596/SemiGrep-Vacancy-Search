from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .ai import ask_ai
from .models import Application, FavoriteVacancy, UserProfile, Vacancy


def _image_upload_error(image, label):
    if not image:
        return None
    if image.size > 5 * 1024 * 1024:
        return "Размер изображения не должен превышать 5 МБ."
    image.seek(0)
    header = image.read(12)
    image.seek(0)
    is_image = (
        header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith((b"GIF87a", b"GIF89a"))
        or (header[:4] == b"RIFF" and header[8:12] == b"WEBP")
    )
    return None if is_image else f"Загрузите {label} в формате JPG, PNG, GIF или WebP."


def _vacancy_image_error(image):
    return _image_upload_error(image, "фото")


def register(request):
    error = None
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if not username or not password:
            error = "Username and password are required."
        elif User.objects.filter(username=username).exists():
            error = "This username is already taken."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error = " ".join(exc.messages)
            if not error:
                user = User.objects.create_user(username=username, password=password)
                login(request, user)
                if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    return redirect(next_url)
                return redirect("vacancy_list")
    return render(request, "core/auth.html", {"title": "Register", "error": error, "next": next_url})


def login_view(request):
    error = None
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("username"), password=request.POST.get("password"))
        if user:
            login(request, user)
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect("vacancy_list")
        error = "Invalid username or password."
    return render(request, "core/auth.html", {"title": "Log in", "error": error, "next": next_url})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("vacancy_list")


@login_required
def profile(request):
    return _render_profile(request, request.user)

@login_required
def update_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        avatar = request.FILES.get("avatar")
        error = _image_upload_error(avatar, "аватар")
        if error:
            return render(request, "core/update_profile.html", {"profile": profile, "error": error})

        old_avatar = profile.avatar
        if avatar:
            profile.avatar = avatar
            try:
                profile.full_clean()
            except ValidationError as exc:
                profile.avatar = old_avatar
                return render(request, "core/update_profile.html", {
                    "profile": profile, "error": " ".join(exc.messages),
                })
        request.user.first_name = request.POST.get("first_name", "")
        request.user.last_name = request.POST.get("last_name", "")
        request.user.email = request.POST.get("email", "")
        request.user.save()
        if avatar:
            profile.save()
            if old_avatar:
                old_avatar.delete(save=False)
        return redirect("profile")
    return render(request, "core/update_profile.html", {"profile": profile})


def _render_profile(request, profile_user):
    profile = UserProfile.objects.filter(user=profile_user).first()
    vacancies = Vacancy.objects.filter(creator=profile_user).order_by("-id")
    return render(request, "core/public_profile.html", {
        "profile_user": profile_user,
        "profile": profile,
        "vacancies": vacancies,
    })


def public_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    return _render_profile(request, profile_user)


def vacancy_list(request):
    vacancies = Vacancy.objects.select_related("creator").order_by("-id")
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(FavoriteVacancy.objects.filter(user=request.user).values_list("vacancy_id", flat=True))
    return render(request, "core/vacancy_list.html", {
        "vacancies": vacancies,
        "favorite_ids": favorite_ids,
        "current_url": request.get_full_path(),
    })


def vacancy_detail(request, pk):
    vacancy = get_object_or_404(Vacancy.objects.select_related("creator"), pk=pk)
    is_favorite = request.user.is_authenticated and FavoriteVacancy.objects.filter(
        user=request.user, vacancy=vacancy,
    ).exists()
    has_applied = request.user.is_authenticated and Application.objects.filter(
        applicant=request.user, vacancy=vacancy,
    ).exists()
    return render(request, "core/vacancy_detail.html", {
        "vacancy": vacancy,
        "is_favorite": is_favorite,
        "has_applied": has_applied,
    })


@login_required
def favorite_list(request):
    favorites = FavoriteVacancy.objects.filter(user=request.user).select_related(
        "vacancy", "vacancy__creator",
    )
    return render(request, "core/favorite_list.html", {"favorites": favorites})


@login_required
@require_POST
def toggle_favorite(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    favorite, created = FavoriteVacancy.objects.get_or_create(user=request.user, vacancy=vacancy)
    if not created:
        favorite.delete()
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect("vacancy_detail", pk=vacancy.pk)


@login_required
def vacancy_form(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        image = request.FILES.get("image")
        vacancy = Vacancy(title=title, description=description, creator=request.user)
        error = None
        image_error = _vacancy_image_error(image)

        if not title or not description:
            error = "Заполните название и описание вакансии."
        elif image_error:
            error = image_error
        else:
            if image:
                vacancy.image = image
            try:
                vacancy.full_clean()
            except ValidationError as exc:
                error = " ".join(exc.messages)

        if error:
            return render(request, "core/vacancy_form.html", {
                "vacancy": None, "title": title, "description": description,
                "form_submitted": True, "error": error,
            })
        vacancy.save()
        return redirect("vacancy_list")

    return render(request, "core/vacancy_form.html", {"vacancy": None})

@login_required
def vacancy_update(request, pk):
    vacancy = get_object_or_404(Vacancy, id=pk)
    if vacancy.creator_id != request.user.id and not request.user.has_perm("core.manage_vacancies"):
        return redirect("vacancy_list")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        image = request.FILES.get("image")
        previous_image = vacancy.image
        error = None
        image_error = _vacancy_image_error(image)

        if not title or not description:
            error = "Заполните название и описание вакансии."
        elif image_error:
            error = image_error
        else:
            vacancy.title = title
            vacancy.description = description
            if image:
                vacancy.image = image
            try:
                vacancy.full_clean()
            except ValidationError as exc:
                error = " ".join(exc.messages)

        if error:
            vacancy.image = previous_image
            return render(request, "core/vacancy_form.html", {
                "vacancy": vacancy, "title": title, "description": description,
                "form_submitted": True, "error": error,
            })

        vacancy.save()
        if image and previous_image:
            previous_image.delete(save=False)
        return redirect("vacancy_list")
    return render(request, "core/vacancy_form.html", {"vacancy": vacancy})

@login_required
@require_POST
def vacancy_delete(request, pk):
    vacancy = get_object_or_404(Vacancy, id=pk)
    if request.user == vacancy.creator or request.user.has_perm("core.manage_vacancies"):
        image = vacancy.image
        vacancy.delete()
        if image:
            image.delete(save=False)
    return redirect("vacancy_list")


@login_required
def application_list(request):
    apps = Application.objects.select_related("vacancy", "applicant")
    if not request.user.has_perm("core.manage_applications"):
        apps = apps.filter(applicant=request.user)
    return render(request, "core/application_list.html", {"applications": apps})


@login_required
def application_create(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id)
    if vacancy.creator_id == request.user.id:
        return redirect("vacancy_list")
    if Application.objects.filter(vacancy=vacancy, applicant=request.user).exists():
        return redirect("application_list")

    form_data = request.POST if request.method == "POST" else {}
    error = None
    if request.method == "POST":
        full_name = request.POST.get("applicant_full_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        messenger = request.POST.get("messenger", "").strip()
        messenger_contact = request.POST.get("messenger_contact", "").strip()

        if not all((full_name, phone_number, messenger, messenger_contact)):
            error = "Заполните ФИО, телефон и контакт в мессенджере."
        elif len(full_name) > 150 or len(phone_number) > 32 or len(messenger_contact) > 100:
            error = "Проверьте длину ФИО и контактных данных."
        elif messenger not in Application.Messenger.values:
            error = "Выберите Telegram или WhatsApp."
        else:
            Application.objects.create(
                vacancy=vacancy,
                applicant=request.user,
                applicant_full_name=full_name,
                phone_number=phone_number,
                messenger=messenger,
                messenger_contact=messenger_contact,
            )
            return redirect("application_list")

    return render(request, "core/application_create.html", {
        "vacancy": vacancy,
        "messenger_choices": Application.Messenger.choices,
        "form_data": form_data,
        "error": error,
    })


@login_required
@require_POST
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if application.applicant_id == request.user.id or request.user.has_perm("core.manage_applications"):
        application.delete()
    return redirect("application_list")


@login_required
def application_update(request, pk):
    application = get_object_or_404(Application.objects.select_related("vacancy"), pk=pk)
    allowed = application.vacancy.creator_id == request.user.id or request.user.has_perm("core.manage_applications")
    if not allowed:
        return redirect("application_list")
    if request.method == "POST":
        status = request.POST.get("status")
        if status in Application.Status.values:
            application.status = status
            application.save()
            return redirect("my_vacancy_applications" if application.vacancy.creator_id == request.user.id else "application_list")
    return render(request, "core/application_form.html", {"application": application, "statuses": Application.Status.choices})

@login_required
def request_to_my_vacancy(request):
    requests = Application.objects.filter(vacancy__creator=request.user).select_related(
        "vacancy", "applicant"
    ).order_by("-created_at")
    return render(request, "core/request_to_my_vacancy.html", {"requests": requests})

@login_required
def send_message_to_ai(request):
    messages = request.session.get("ai_chat", [])[-12:]
    error = None
    vacancy_id = request.POST.get("vacancy_id") if request.method == "POST" else request.GET.get("vacancy_id")
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id) if vacancy_id else None
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if message:
            messages.append({"role": "user", "content": message})
            vacancy_context = None
            if vacancy:
                vacancy_context = {
                    "title": vacancy.title,
                    "description": vacancy.description[:10000],
                    "employer": vacancy.creator.username,
                }
            try:
                answer = ask_ai(messages[-12:], vacancy_context=vacancy_context)
            except Exception:
                answer = "Сейчас не удалось связаться с ИИ. Попробуйте ещё раз немного позже."
                error = answer
            messages.append({"role": "assistant", "content": answer})
            messages = messages[-12:]
            request.session["ai_chat"] = messages
        else:
            error = "Введите вопрос для ИИ."
    return render(request, "core/ai.html", {"messages": messages, "error": error, "vacancy": vacancy})
