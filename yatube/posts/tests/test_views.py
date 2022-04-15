import shutil
import tempfile

from django.conf import settings
from django import forms
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.core.cache import cache

from ..forms import PostForm
from ..models import Group, Post, User, Comment, Follow


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_user')
        cls.author_1 = User.objects.create_user(username='test_user_1')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.new_group = Group.objects.create(
            title='Тестовый заголовок 1',
            slug='test_slug_1',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый заголовок',
            image=cls.uploaded,
        )
        cls.form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        cls.templates_pages_names = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': cls.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': cls.post.author}
            ),
        ]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ),
            'posts/profile.html': (
                reverse('posts:profile', kwargs={'username': 'test_user'})
            ),
            'posts/post_detail.html': (
                reverse('posts:post_detail', kwargs={'post_id': '1'})
            ),
            'posts/create_post.html': reverse('posts:create_post'),
        }

        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_index_page_show_correct_context(self):
        """Шаблон страницы index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        context_objects = {
            self.post.author: first_object.author,
            self.post.text: first_object.text,
            self.group: first_object.group,
            self.post.id: first_object.id,
        }
        for reverse_name, response_name in context_objects.items():
            with self.subTest(reverse_name=reverse_name):
                self.assertEqual(response_name, reverse_name)

    def test_group_pages_show_correct_context(self):
        """Шаблон страницы group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        first_object = response.context['page_obj'][0]
        context_objects = {
            self.post.author: first_object.author,
            self.group: first_object.group,
            self.post.id: first_object.id,
        }
        for reverse_name, response_name in context_objects.items():
            with self.subTest(reverse_name=reverse_name):
                self.assertEqual(response_name, reverse_name)

    def test_create_page_show_correct_context(self):
        """Шаблон страницы post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:create_post'))
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:update_post', kwargs={'post_id': '1'})
        )
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertIsInstance(response.context.get('form'), PostForm)
        self.assertTrue('is_edit' in response.context)
        self.assertTrue(response.context['is_edit'], True)

    def test_post_profile_page_show_correct_context(self):
        """Шаблон страницы profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        first_object = response.context['page_obj'][0]
        context_objects = {
            self.author: first_object.author,
            self.post.text: first_object.text,
            self.group: first_object.group,
            self.post.id: first_object.id,
        }
        for reverse_name, response_name in context_objects.items():
            with self.subTest(reverse_name=reverse_name):
                self.assertEqual(response_name, reverse_name)

    def test_image_in_context(self):
        """При выводе поста с картинкой изображение передаётся в словаре
        context на страницы index, group_list, profile и post_detail.
        """
        for pages_names in self.templates_pages_names:
            with self.subTest(pages_names=pages_names):
                response = self.authorized_client.get(pages_names)
                self.assertTrue(response.context['page_obj'][-1].image)
                self.assertEqual(
                    response.context['page_obj'][-1].image,
                    self.post.image
                )
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        self.assertTrue(response.context['post'].image)
        self.assertEqual(
            response.context['post'].image, self.post.image
        )

    def test_post_new_create_appears_on_correct_pages(self):
        """При создании поста, указывая группу, пост появляется на главной странице,
        на странице выбранной группы, в профайле пользователя."""
        pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.author.username})
        ]
        for revers in pages:
            with self.subTest(revers=revers):
                response = self.authorized_client.get(revers)
                self.assertIn(self.post, response.context['page_obj'])

    def test_posts_not_contain_in_wrong_group(self):
        """Пост не попал в группу, для которой не был предназначен."""
        post = Post.objects.get(author=self.author,
                                group=self.group,
                                text='Тестовый заголовок'
                                )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.new_group.slug})
        )
        self.assertNotIn(post, response.context['page_obj'].object_list)

    def test_authorized_client_can_comment(self):
        """Авторизованный пользователь может комментировать посты."""
        comments_initial = Comment.objects.count()
        self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data={'text': 'Комментарий для поста 2'}
        )
        comments_finally = Comment.objects.count()
        comments_text = Comment.objects.all()[0].text
        self.assertEqual(comments_initial + 1, comments_finally)
        self.assertEqual('Комментарий для поста 2', comments_text)

    def test_guest_client_cant_comment(self):
        """Неавторизованный пользователь не может комментировать посты."""
        comments_initial = Comment.objects.count()
        self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data={'text': 'Комментарий для поста 1'}
        )
        comments_finally = Comment.objects.count()
        self.assertNotEqual(comments_initial + 1, comments_finally)

    def test_comment_in_page_detail(self):
        """После успешной отправки комментарий появляется на странице поста."""
        self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data={'text': 'Комментарий для поста 2'}
        )
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        comments_text = response.context['comments'][0].text
        self.assertEqual('Комментарий для поста 2', comments_text)

    def test_cache_home_page(self):
        """Проверка работы кеша главной страницы."""
        post_del_cache = Post.objects.create(
            text='Текст для проверки',
            author=self.author,
        )

        def response():
            return self.guest_client.get(reverse('posts:index'))

        response_primary = response().content
        post_del_cache.delete()
        response_secondary = response().content
        self.assertEqual(response_primary, response_secondary)
        cache.clear()
        response_cache_clear = response().content
        self.assertNotEqual(response_secondary, response_cache_clear)

    def test_authorized_client_can_follow(self):
        """Авторизованный пользователь может подписаться
        на других пользователей.
        """
        follow_obj = Follow.objects.filter(
            user=self.author,
            author=self.author_1
        )
        self.assertFalse(follow_obj)
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.author_1.username}
        ))
        follow_obj = Follow.objects.filter(
            user=self.author,
            author=self.author_1
        )
        self.assertTrue(follow_obj)

    def test_authorized_client_can_unfollow(self):
        """Авторизованный пользователь может отписаться
        от других пользователей.
        """
        follow_obj = Follow.objects.create(
            user=self.author,
            author=self.author_1
        )
        self.assertTrue(follow_obj)
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author_1.username}
        ))
        follow_obj = Follow.objects.filter(
            user=self.author,
            author=self.author_1
        )
        self.assertFalse(follow_obj)

    def test_new_post_add_follower_not_add_unfollower(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан.
        """
        user_1 = User.objects.create_user(username='Тестовый юзер 1')
        Follow.objects.create(user=self.author, author=user_1)
        new_post = Post.objects.create(author=user_1, text='Новый пост')
        response_1 = self.authorized_client.get(reverse('posts:follow_index'))
        self.authorized_client.get(reverse('users:logout'))
        user_2 = Client()
        user_2.force_login(self.author_1)
        response_2 = user_2.get(reverse('posts:follow_index'))
        new_post_follow_1 = response_1.context['page_obj'].object_list[0]
        self.assertEqual(new_post, new_post_follow_1)
        new_post_follow_2 = response_2.context['page_obj'].object_list
        self.assertFalse(new_post_follow_2)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        objects = [
            Post(
                author=cls.author,
                group=cls.group,
                text='Тестовый заголовок',
            )
            for bulk in range(1, 14)
        ]
        cls.post = Post.objects.bulk_create(objects)

    def test_first_page_contains_ten_records(self):
        """Проверка: количество постов на первой странице равно 10."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """Проверка: количество постов на второй странице равно 3."""
        response = self.client.get(reverse('posts:index'), {'page': 2})
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_group_list_contains_ten_pages(self):
        """Проверка: количество постов на первой
        странице group_list равно 10."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_list_contains_three_records(self):
        """Проверка: количество постов на второй
        странице group_list равно 3."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            {'page': 2}
        )
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_profile_contains_ten_records(self):
        """Проверка: количество постов на странице profile равно 10."""
        response = self.client.get(reverse(
            'posts:profile', kwargs={'username': self.author.username}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_contains_three_records(self):
        """Проверка: количество постов на второй
        странице profile равно 3."""
        response = self.client.get(reverse(
            'posts:profile', kwargs={'username': self.author.username}),
            {'page': 2}
        )
        self.assertEqual(len(response.context['page_obj']), 3)
