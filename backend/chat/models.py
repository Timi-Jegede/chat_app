from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.

class Message(models.Model):

    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages', 
        verbose_name='Sender of the message'
    )

    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages', 
        null=True, blank=True,
        verbose_name='Receiver of the message (optional)'
    )

    content = models.TextField(verbose_name='Message content')

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp of the message')

    thread_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='Name of the chat thread/room')

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        if self.receiver:
            return f'From {self.sender.username} to {self.receiver.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}'
        else:
            return f'From {self.sender.username} in {self.thread_name} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}'
    
        #def save(self, *args, **kwargs):
        #    if not self.thread_name:
        #        self.thread_name = f'{self.sender.username}_{self.receiver.username}'

    @staticmethod
    def get_thread_name(user_id, other_user_id):
        user_id = int(user_id)
        other_user_id = int(other_user_id)
        #print(f"Creating thread name for users {user_id} and {other_user_id}")
        try:
            result = f"chat_{min(user_id, other_user_id)}_{max(user_id, other_user_id)}"
            #print(f"Thread name result: {result}")
            return result
        except Exception as e:
            #print(f"Error creating thread name: {e}")
            raise
    
class Profile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name='User associated with the profile',
        related_name='profile'
    )

    bio = models.TextField(blank=True, verbose_name='User biography')

    status = models.CharField(max_length=255, blank=True, verbose_name='User status message')

    birthdate = models.DateField(null=True, blank=True, verbose_name='User birthdate')

    language = models.CharField(max_length=50, null=True, blank=True, verbose_name='Preferred language')

    city = models.CharField(max_length=100, null=True, blank=True, verbose_name='City of residence')

    gender = models.CharField(max_length=20, null=True, blank=True, verbose_name='User gender')

    phone_no = models.CharField(max_length=20, null=True, blank=True, verbose_name='Contact phone number')

    nickname = models.CharField(max_length=50, null=True, blank=True, verbose_name='User nickname')

    photo = models.ImageField(upload_to='user_photos/', blank=True, null=True, verbose_name='Profile picture')

    last_seen = models.DateTimeField(null=True, blank=True, auto_now=True, verbose_name='Last seen timestamp')

    header_img = models.ImageField(upload_to='header_images/', blank=True, null=True, verbose_name='Header image')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Profile creation timestamp')
    
    updated_at = models.DateTimeField(auto_now_add=True, verbose_name='Profile last update timestamp')

    def __str__(self):
        return f'{self.user.username} Profile'
    
class Contact(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='contacts', 
        verbose_name='Owner of the contact list'
    )

    contact = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='in_contact_lists', 
        verbose_name='Contact user'
    )

    is_favorite = models.BooleanField(default=False, verbose_name='Is the contact marked as favorite?')

    blocked = models.BooleanField(default=False, verbose_name='Is the contact blocked?')

    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp when the contact was added')

    removed_at = models.DateTimeField(null=True, blank=True, verbose_name='Timestamp when the contact was removed')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'contact'], name='unique_user_contact')
        ]
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'

    def __str__(self):
        return f'{self.user.username} -> {self.contact.username}'

class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='User who received the notification'
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        verbose_name='User who sent the notification'
    )

    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name='notification',
        verbose_name='Associated message notification'
    )

    content = models.TextField(verbose_name='Notification message')

    is_read = models.BooleanField(default=False, verbose_name='Has the notification been read?')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp of notification creation')

    def __str__(self):
        return f'{self.user.username} - {self.message}'
    
class SharedFile(models.Model):
    file = models.FileField(upload_to='shared_files/', blank=True, null=True, verbose_name='Shared file')

    image = models.ImageField(upload_to='shared_images/', blank=True, null=True, verbose_name='Shared image')

    image_caption = models.TextField(blank=True, null=True, verbose_name='Image caption')

    link = models.URLField(max_length=2000, blank=True, null=True, verbose_name='Shared link')

    video = models.FileField(upload_to='shared_videos/', blank=True, null=True, verbose_name='Shared video')

    audio = models.FileField(upload_to='audio/', null=True, blank=True)

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_files',
        verbose_name='User who sent the file'
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_files',
        verbose_name='User who received the file'
    )

    thread_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='Name of the chat thread/room')

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp of file sharing')

    def __str__(self):
        return f'{self.sender.username} -> {self.receiver.username} : {self.file.name}'

class BackgroundOption(models.Model):
    name = models.CharField(max_length=100, verbose_name='Background name')

    image = models.ImageField(upload_to='backgrounds/', verbose_name='Background image')

    is_active = models.BooleanField(default=True, verbose_name='Is available for selection')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creation timestamp')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Archive(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='archives',
        verbose_name='User who archived the chat'
    )

    other_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='archived_by_others',
        verbose_name='The other user in the archived chat'
    )

    thread_name = models.CharField(max_length=255, verbose_name='Name of the archived chat thread/room')

    archived_at = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp when the chat was archived')

    is_active = models.BooleanField(default=True, verbose_name='Is the archive active?')

    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'Chat Archive'
        verbose_name_plural = 'Chat Archives'

    def __str__(self):
        return f'{self.user.username} archived {self.thread_name} at {self.archived_at.strftime('%Y-%m-%d %H:%M')}'