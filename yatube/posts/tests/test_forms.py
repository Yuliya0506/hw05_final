import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Post, Group, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый заголовок',
        )
        cls.form_data = {
            'text': PostFormTest.post.text,
            'group': PostFormTest.group.id
        }
        cls.post_obj_filter = Post.objects.filter(
            id=PostFormTest.post.id,
            text=PostFormTest.post.text,
            group=PostFormTest.group.id,
        )
        cls.form = PostForm()
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_form_create(self):
        """Валидная форма создает пост."""
        post_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:create_post'),
            data=self.form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.author.username}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(self.post_obj_filter.exists())

    def test_no_authorized_person_cant_create_post(self):
        """Не авторизованный пользователь
        не может создать пост"""
        post_count = Post.objects.count()
        response_1 = self.guest_client.post(
            reverse('posts:create_post'),
            data=self.form_data,
            follow=True
        )
        self.assertRedirects(response_1, ('/auth/login/?next=/create/'))
        self.assertEqual(Post.objects.count(), post_count)
        self.assertTrue(self.post_obj_filter.exists())

    def test_post_edit(self):
        """При отправке валидной формы пост редактируется."""
        text_edit = 'Отредактированный текст'
        posts_count = Post.objects.count()
        form_data = {
            'text': text_edit,
            'group': PostFormTest.group.id
        }
        response_1 = self.authorized_client.post(
            reverse('posts:update_post',
                    kwargs={'post_id': PostFormTest.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response_1, reverse(
            'posts:post_detail', kwargs={'post_id': PostFormTest.post.id}), )

        self.assertTrue(Post.objects.filter(
            group=PostFormTest.group.id,
            id=PostFormTest.post.id,
            text=text_edit,
        ).exists())
        self.assertEqual(Post.objects.count(), posts_count)

    def test_no_authorized_person_cant_edit_post(self):
        """Не авторизованный пользователь
        не может редактировать пост"""
        posts_count = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:update_post', kwargs={'post_id': '1'}),
            data=self.form_data,
            follow=True
        )
        self.assertRedirects(response, ('/auth/login/?next=/posts/1/edit/'))
        self.assertEqual(Post.objects.count(), posts_count)

    def test_create_post_with_image(self):
        """При отправке поста с картинкой через форму PostForm
        создаётся запись в базе данных.
        """
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'author': self.author,
            'image': uploaded,
        }
        posts_count = Post.objects.count()
        self.authorized_client.post(
            reverse('posts:create_post'),
            data=form_data,
            follow=True)
        post_with_image = Post.objects.get(text='Тестовый текст')
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(post_with_image.text, form_data['text'])
        self.assertEqual(post_with_image.group.id, form_data['group'])
        self.assertEqual(post_with_image.author, form_data['author'])
        self.assertEqual(post_with_image.image, 'posts/small.gif')
