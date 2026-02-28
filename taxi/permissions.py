from rest_framework import permissions
from django.contrib.auth import get_user_model
from taxi.models import Trip

User = get_user_model()


def has_role(user, role_code):
    """Проверяет, есть ли у пользователя роль с заданным code."""
    if not user.is_authenticated:
        return False
    return user.userrole_set.filter(role__code=role_code).exists()


class IsAuthenticatedAndActive(permissions.BasePermission):
    """Пользователь должен быть аутентифицирован и активен."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_active', False)
        )


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'admin')


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'customer')


class IsDriver(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'driver')


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешает доступ, если:
      - пользователь — владелец объекта (например, профиль, авто, поездка),
      - или админ.
    Предполагается, что объект имеет FK `user` или `customer`/`driver`.
    """
    def has_object_permission(self, request, view, obj):
        if has_role(request.user, 'admin'):
            return True

        # Поддерживаемые случаи:
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        if hasattr(obj, 'customer') and obj.customer == request.user:
            return True
        if hasattr(obj, 'driver') and obj.driver == request.user:
            return True
        if hasattr(obj, 'driver_id') and obj.driver_id == request.user.id:
            return True
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True

        return False


class IsTripParticipantOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if has_role(request.user, 'admin'):
            return True

        # If updating status to 'accepted', allow any driver
        if (
            request.method == 'PATCH' and
            isinstance(obj, Trip) and
            obj.status == 'requested' and
            request.data.get('status') == 'accepted' and
            has_role(request.user, 'driver')
        ):
            return True

        # Otherwise, must be actual participant
        return obj.customer == request.user or obj.driver == request.user


class IsActiveDriver(permissions.BasePermission):
    """
    Только водитель с активным автомобилем может обновлять геолокацию.
    """
    def has_permission(self, request, view):
        if not has_role(request.user, 'driver'):
            return False

        # Проверяем, есть ли у водителя хотя бы один активный автомобиль
        return request.user.cars.filter(is_active=True).exists()


class IsCarOwner(permissions.BasePermission):
    """
    Только владелец автомобиля может его редактировать.
    """
    def has_object_permission(self, request, view, obj):
        if has_role(request.user, 'admin'):
            return True
        return obj.driver == request.user


class ReadOnlyForAll(permissions.BasePermission):
    """
    GET, HEAD, OPTIONS разрешены всем; остальное — только админу.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return has_role(request.user, 'admin')  