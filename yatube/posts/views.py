from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm


POSTS_ON_PAGE = 10


def index(request):
    posts = Post.objects.all()
    text = 'Последние обновления на сайте'
    paginator = Paginator(posts, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'title': f'Главная страница: {text}',
        'text': text,
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.filter(group=group)
    paginator = Paginator(posts, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    title = group.title
    context = {
        'title': title,
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = Post.objects.filter(
        author=author).select_related('author', 'group')
    count_posts = posts.count()
    paginator = Paginator(posts, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    following = Follow.objects.filter(
        user=request.user.id,
        author=author.id
    ).exists()
    context = {
        'count_posts': count_posts,
        'page_obj': page_obj,
        'title': f'Профайл пользователя {username}',
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author_posts = Post.objects.filter(author=post.author).count()
    group_name = post.group
    form = CommentForm()
    comments = post.comments.filter(post=post_id)
    context = {
        'title': group_name,
        'post': post,
        'author_posts': author_posts,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        form.save()
        return redirect('posts:profile', username=request.user)

    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post)
    if form.is_valid():
        post = form.save()
        return redirect('posts:post_detail', post_id)
    return render(request, 'posts/update_post.html', {
        'form': form, 'is_edit': True, 'post': post})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    content = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', content)


@login_required
def profile_follow(request, username):
    author_obj = get_object_or_404(User, username=username)
    user_obj = request.user
    follow_obj = Follow.objects.filter(
        user=user_obj,
        author=author_obj
    )
    if not follow_obj.exists() and author_obj != user_obj:
        Follow.objects.create(user=user_obj, author=author_obj)
    return redirect('posts:profile', username=author_obj.username)


@login_required
def profile_unfollow(request, username):
    author_obj = get_object_or_404(User, username=username)
    user_obj = request.user
    follow_obj = Follow.objects.filter(
        user=user_obj,
        author=author_obj
    )
    if follow_obj.exists():
        follow_obj.delete()
    return redirect('posts:profile', username=author_obj.username)
