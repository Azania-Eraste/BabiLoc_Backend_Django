from rest_framework import permissions

class IsVendor(permissions.BasePermission):
    """Permission pour les vendeurs/propriétaires vérifiés"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_vendor and 
            request.user.est_verifie
        )


class IsSupportOrAdmin(permissions.BasePermission):
    """Allow access to support users (is_support) or staff/admin users.

    This is used to permit support agents to access admin-style chat signalement
    views without granting full superuser rights.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and (
                getattr(user, 'is_support', False) or user.is_staff or user.is_superuser
            )
        )
