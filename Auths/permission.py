from rest_framework import permissions

class IsVendor(permissions.BasePermission):
    """Permission pour les vendeurs/propriétaires vérifiés"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_vendor and 
            request.user.est_verifie
        )
