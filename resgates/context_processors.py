from .models import Profile


def active_profile(request):
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return {"active_profile": profile}
    return {"active_profile": None}
