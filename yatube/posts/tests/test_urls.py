from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post


User = get_user_model()


class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.user_1 = User.objects.create_user(username='test_user_1')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая запись для создания нового поста'
        )
        cls.post_1 = Post.objects.create(
            author=cls.user_1,
            text='Тестовая запись для создания нового поста'
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.url_names = (
            '/',
            '/group/test-slug/',
            '/profile/test_user/',
            '/posts/1/'
        )
        cls.templates_url_names = {
            'posts/index.html': '',
            'posts/group_list.html': '/group/test-slug/',
            'posts/profile.html': '/profile/test_user/',
            'posts/post_detail.html': '/posts/1/',
            'posts/create_post.html': '/create/',
        }

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client_1 = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_exists_at_desired_location(self):
        """Страница доступна любому пользователю."""
        for adress in self.url_names:
            with self.subTest():
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

        # Проверяем доступность страниц для авторизованного пользователя
    def test_post_create_url_exists_at_desired_location_authorized(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/', follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_exists_at_desired_location(self):
        """Страница posts/<post_id>/edit/ доступна автору поста."""
        response = self.authorized_client.get('/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_no_author_of_post_cant_edit_post(self):
        """Страница posts/<post_id>/edit/ не доступна
         авторизованному пользователю, но не автору поста"""
        response = self.authorized_client_1.get('/posts/1/edit/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_url_redirect_anonymous(self):
        """Страница create/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_post_edit_url_redirect_anonymous(self):
        """Страница post_edit/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get('/posts/1/edit/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for template, url in self.templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_redirect_for_authorized_client(self):
        """При обращении к странице редактирования авторизованного
        пользователя, но не автора поста, должен проверяться редирект.
        """
        response = self.authorized_client.get(
            reverse('posts:update_post', kwargs={'post_id': self.post_1.id})
        )
        redirect_url = reverse(
            'posts:post_detail', kwargs={'post_id': self.post_1.id}
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, redirect_url)

    def test_page_404(self):
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
