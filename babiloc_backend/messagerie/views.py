from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Message, Conversation
from .forms import MessageForm

# Supprimez ou commentez la vue accueil
# def accueil(request):
#     """Vue pour la page d'accueil"""
#     return render(request, 'messagerie/login.html', {})

@login_required
def boite_reception(request):
    """Affiche la boîte de réception de l'utilisateur"""
    messages_recus = Message.objects.filter(
        destinataire=request.user,
        archive_destinataire=False
    ).order_by('-timestamp')
    paginator = Paginator(messages_recus, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'messages': page_obj,
        'title': 'Boîte de réception'
    }
    return render(request, 'messagerie/boite_reception.html', context)

@login_required
def messages_envoyes(request):
    """Affiche les messages envoyés par l'utilisateur"""
    messages_envoyes = Message.objects.filter(
        expediteur=request.user,
        archive_expediteur=False
    ).order_by('-timestamp')
    paginator = Paginator(messages_envoyes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'messages': page_obj,
        'title': 'Messages envoyés'
    }
    return render(request, 'messagerie/messages_envoyes.html', context)

@login_required
def nouveau_message(request, destinataire_id=None):
    """Créer un nouveau message"""
    destinataire = None
    if destinataire_id:
        destinataire = get_object_or_404(User, id=destinataire_id)
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.expediteur = request.user
            message.save()
            conversation = Conversation.get_or_create_conversation(request.user, message.destinataire)
            conversation.dernier_message = message
            conversation.save()
            messages.success(request, 'Message envoyé avec succès!')
            return redirect('messagerie:boite_reception')
    else:
        initial_data = {}
        if destinataire:
            initial_data['destinataire'] = destinataire
        form = MessageForm(initial=initial_data)
    context = {
        'form': form,
        'destinataire': destinataire,
        'title': 'Nouveau message'
    }
    return render(request, 'messagerie/nouveau_message.html', context)

@login_required
def lire_message(request, message_id):
    """Afficher un message spécifique"""
    message = get_object_or_404(
        Message,
        id=message_id,
        **{'$or': Q(expediteur=request.user) | Q(destinataire=request.user)}
    )
    if message.destinataire == request.user and not message.lu:
        message.marquer_comme_lu()
    context = {
        'message': message,
        'title': f'Message: {message.objet}'
    }
    return render(request, 'messagerie/lire_message.html', context)

@login_required
def conversations(request):
    """Affiche toutes les conversations de l'utilisateur"""
    conversations = Conversation.objects.filter(
        participants=request.user
    ).order_by('-mise_a_jour')
    context = {
        'conversations': conversations,
        'title': 'Mes conversations'
    }
    return render(request, 'messagerie/conversations.html', context)

@login_required
def voir_conversation(request, conversation_id):
    """Affiche une conversation spécifique"""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    messages_conversation = conversation.get_messages()
    messages_non_lus = messages_conversation.filter(
        destinataire=request.user,
        lu=False
    )
    messages_non_lus.update(lu=True)
    context = {
        'conversation': conversation,
        'messages': messages_conversation,
        'title': f'Conversation avec {conversation.participants.exclude(id=request.user.id).first()}'
    }
    return render(request, 'messagerie/conversation_detail.html', context)