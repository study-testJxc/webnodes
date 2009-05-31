# Django imports
from django.shortcuts import render_to_response
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.core.cache import cache
from django.utils.cache import get_cache_key
from django import forms
from django.utils import simplejson

# Local imports
import reddit
from models import Group, Topic, Comment, Tag


### Helper functions ###
def expire_page(path):
    request = HttpRequest()
    request.path = path
    key = get_cache_key(request)
    cache.delete(key)


### Forms ###
class TopicForm(forms.Form):
    title = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea)
    tags = forms.CharField(required=False)
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        tags = tags.split(',')
        return [str(slugify(tag)) for tag in tags]
        

class GroupForm(forms.Form):
    title = forms.CharField(max_length=200)
    name = forms.CharField(max_length=100)
    
    def clean_name(self):
        name = self.cleaned_data['name']
        if not name:
            raise forms.ValidationError('Enter a name for your group')
        if name != slugify(name):
            raise forms.ValidationError('Names may only contain letters, numbers, dashes and underscores.')
        return name
        
        
### Request handlers ###
def index(request):
    pass

def groups_new(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = Group.get_or_insert(
                key_name=form.cleaned_data['name'],
                title=form.cleaned_data['title']
            )
            return HttpResponseRedirect('/' + group.name)
    else:
        form = GroupForm()
    
    return render_to_response('basic_form.html', {
        'form': form
    }, context_instance=RequestContext(request))

def topics(request, group):
    return render_to_response('topics.html', {
        'group': group,
        'topics': Topic.recent_topics(group),
        'tags': Tag.top_tags()
    }, context_instance=RequestContext(request))

def topics_new(request, group):
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            group = Group.get_by_key_name(group)
            topic = Topic(
                author=request.user.username,
                group=group.name,
                title=form.cleaned_data['title'],
                body=form.cleaned_data['body'],
                tags=form.cleaned_data['tags']
            )
            topic.put()
            redirect = '/'+ group + '/' + str(topic.id)
            expire_page(redirect)
            return HttpResponseRedirect(redirect)
    else:
        form = TopicForm()
    
    return render_to_response('basic_form.html', {
        'form': form
    }, context_instance=RequestContext(request))

def topic(request, group, id):
    topic = Topic.get_by_id(int(id))
    if request.method == 'POST':
        parent_id = request.POST['parent_id']
        parent = Comment.get_by_id(int(parent_id)) if parent_id else topic
        parent.add_reply(
            author=request.user.username, 
            body=request.POST['body']
        )
        expire_page('/topics/' + str(topic.id))
    return render_to_response('topic.html', {
        'topic': topic,
        'group': group,
        'comments': topic.comments,
        'graph': simplejson.dumps(topic.comment_graph),
    }, context_instance=RequestContext(request))


def topic_edit(request, group, id):
    topic = Topic.get_by_id(int(id))
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic.edit()
            redirect = '/'+ group + '/' + str(topic.id)
            expire_page(redirect)
            return HttpResponseRedirect(redirect)
    else:
        form = TopicForm()
    
    return render_to_response('basic_form.html', {
        'form': form
    }, context_instance=RequestContext(request))


def reddit_topics(request):
    return render_to_response('topics.html', {
        'topics': reddit.hot_topics(),
        'group': 'reddit'
    }, context_instance=RequestContext(request))

def reddit_topic(request, id):
    data = reddit.get_thread_data(id)
    data['group'] = 'reddit'
    return render_to_response('topic.html', data,
        context_instance=RequestContext(request))
