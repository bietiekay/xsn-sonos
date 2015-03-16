# -*- encoding: utf-8 -*-
# 
# Copyright © 2012 Robert Weidlich. All Rights Reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# 
# 3. The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE LICENSOR "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.
# 
# -*- coding: utf-8 -*-


from django.db import models
from django.db.models.signals import post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from django.db.models import Min, Max
from django.conf import settings

from autoslug import AutoSlugField

import jsonfield
import uuid
import os.path


import os.path
import uuid

class Show(models.Model):
    name = models.CharField(max_length=50, unique=True,
        verbose_name=_('Name of the show'),
    )
    slug = AutoSlugField(populate_from='name', always_update=True)
    url = models.URLField(blank=True, default='',
        verbose_name=_('Homepage of the Show'))
    twitter = models.CharField(max_length=100, blank=True, default='',
        help_text='Name of the associated Twitter account')
    chat = models.CharField(max_length=100, blank=True, default='',
        help_text='Associated IRC network and channel. Contact administrator for unlisted networks.')
    description = models.CharField(max_length=200, blank=True, default='',
        verbose_name=_("Description"))
    abstract = models.TextField(blank=True, default='',
        verbose_name=_('Longer description of the show'))

    LICENCES = (
        ('none', _('none')),
        ('cc-by', _('cc-by')),
        ('cc-by-sa', _('cc-by-sa')),
        ('cc-by-nd', _('cc-by-nd')),
        ('cc-by-nc', _('cc-by-nc')),
        ('cc-by-nc-sa', _('cc-by-nc-sa')),
        ('cc-by-nc-nd', _('cc-by-nc-nd')),
    )

    licence  = models.CharField(max_length=100,
        choices=LICENCES, default=LICENCES[0][0], blank=True,
        verbose_name=_("Licence"))

    defaultShortName = models.SlugField(default='',
        help_text=_('Used to construct the episode' +
                    ' identifier.'),
        verbose_name=_("Abbreviation of the show"))
    nextEpisodeNumber = models.PositiveIntegerField(default=1,
        help_text=_('The number of the next episode to be aired. Used to construct the episode identifier'),
        verbose_name=_("Number of the next episode"))

    icon = models.FileField(upload_to="show-icons/", blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        permissions = (
            ('change_episodes', _('Delete Episodes')),
        )

class ShowFeed(models.Model):
    show = models.OneToOneField(Show)
    enabled = models.BooleanField(verbose_name=_("Enable"), default=False)
    feed = models.URLField(max_length=240, blank=True,
        verbose_name=_("Feed of the podcast"),)
    titlePattern = models.CharField(max_length=240, blank=True,
        verbose_name=_("Regular expression for the title"),
        help_text=_(u"Used to extract the id and title from the »title« field of the feed. Should contain the match groups »id« and »title«. "))
    icalfeed = models.URLField(max_length=255, blank=True,
        verbose_name=_("iCal feed for upcoming shows"))


class Episode(models.Model):
    """
        a single Episode of a show, which should be relayed or was relayed in
        the past
    """

    #available options for dashboard users
    PUBLIC_STATUS = (
        ('ARCHIVED', _("Archived Episode")),
        ('UPCOMING', _("Upcoming Episode")),
    )
    STATUS = (
        ('ARCHIVED', _("Archived Episode")),
        ('RUNNING', _("Running Episode")),
        ('UPCOMING', _("Upcoming Episode")),
    )
    show = models.ForeignKey(Show, verbose_name=_("Show"))
    slug = models.SlugField(max_length=30, default='',
        verbose_name=_("Short Name"))
    
    def begin(self):
        return self.parts.aggregate(Min('begin'))['begin__min']
    
    def end(self):
        return self.parts.aggregate(Max('end'))['end__max']
    
    def title(self):
        if len(self.parts.all()) > 0:
            return self.parts.all()[0].title
        return None
    
    def description(self):
        if len(self.parts.all()) > 0:
            return self.parts.all()[0].description
        return None        
    
    def url(self):
        if len(self.parts.all()) > 0:
            return self.parts.all()[0].url
        return None        
    
    def get_id(self):
        return unicode("%s-%s") % (self.show.slug, self.slug)

    status = models.CharField(max_length=10,
        choices=STATUS, default=STATUS[2][0])

    current_part = models.ForeignKey('EpisodePart', blank=True, null=True, related_name="current_episode")

    def __unicode__(self):
        if len(self.parts.all()) > 0:
            return self.parts.all()[0].__unicode__()
        else:
            return u'%s' % self.slug

#    def save(self, force_insert=False, force_update=False):
#        #if self.title == '':
#        #    self.title = _("Episode %(number)s of %(show)s") % \
#        #                    {'number': self.slug, 'show': self.show.name}
#        self.slug = self.slug.lower()
#        if self.slug == re.sub("\W", "", self.title):
#            self.title = ""
#        super(Episode, self).save(force_insert, force_update)

    class Meta:
        unique_together = (('show', 'slug'),)


class EpisodePart(models.Model):
    """
    a part of an episode, i.e 'intro' or 'interview with first caller'
    should be used for timelines
    """
    episode = models.ForeignKey(Episode, related_name='parts')
    title = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Topic"))
    description = models.CharField(max_length=200, blank=True,
        default='', verbose_name=_("Description"))    
    begin = models.DateTimeField(verbose_name=_("Begin"))
    end = models.DateTimeField(blank=True, null=True, verbose_name=_("End"))
    url = models.URLField(blank=True,
        help_text=_('Page of the Episode'),
        verbose_name=_("URL"))

    def __unicode__(self):
        return u'%s%s%s' % (self.episode.slug, " " if self.title else"", self.title, )

    class Meta:
        ordering = ['-id']


class Marker(models.Model):
    episode = models.ForeignKey(EpisodePart)
    pointoftime = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    link = models.URLField(blank=True)
    delete = models.BooleanField(default=True)


GTYPES = (
    ('server', _("Listener Statistics Grouped by Server")),
    ('mount', _("Listener Statistics Grouped by Mount Point")),
)


def get_graphic_path(instance, filename):
    dn = "/".join(["graphics", 
              instance.episode.episode.show.slug])
    fn = "%s.png" % uuid.uuid4()
    fdn = os.path.join(settings.MEDIA_ROOT, dn)
    if not os.path.exists(fdn):
        os.makedirs(fdn)
    return "/".join([dn, fn])


class Graphic(models.Model):
    file = models.FileField(upload_to=get_graphic_path, blank=True)
    type = models.CharField(max_length=10, choices=GTYPES, default='')
    episode = models.ForeignKey('EpisodePart', related_name='graphics')

    def __unicode__(self):
        return self.file.name + unicode(": ") + unicode(self.episode)


class Recording(models.Model):
    episode = models.ForeignKey('EpisodePart', related_name='recordings')
    path = models.CharField(max_length=250, unique=True)

    format = models.CharField(max_length=50)
    bitrate = models.CharField(max_length=50)

    publicURL = models.URLField(default='')
    isPublic = models.BooleanField(default=False)
    size = models.PositiveIntegerField()
    
    running = models.BooleanField(default=False)

    def __unicode__(self):
        return self.path


class Channel(models.Model):
    # Status
    #running = models.BooleanField(default=False,
    #    help_text=_("A Stream of this channel is running"))
    def running(self):
        return self.stream_set.filter(running=True).count() > 0

    # Meta data from stream
    cluster = models.CharField(max_length=40, unique=True,
        help_text=_("Stream identifier from backend"))
    streamCurrentSong = models.CharField(max_length=255,
        blank=True, default='',
        help_text=_(u"Property »current_song« from stream meta data"))
    streamGenre = models.CharField(max_length=250, blank=True, default='',
        help_text=_(u"Property »genre« from stream meta data"))
    streamShow = models.CharField(max_length=250, blank=True, default='',
        help_text=_(u"Property »show« from stream meta data"))
    streamDescription = models.CharField(max_length=250,
        blank=True, default='',
        help_text=_(u"Property »description« from stream meta data"))
    streamURL = models.URLField(blank=True, default='',
        help_text=_(u"Property »url« from stream meta data"))

    show = models.ManyToManyField(Show, blank=True, null=True,
        help_text=_('show which is assigned to this channel'),
        verbose_name=_('Associated shows'))

    mapping_method = jsonfield.JSONField(
        verbose_name=_('Method for mapping between streams and episodes'),
        help_text=_('Configure order for mapping methods. Use drop-down box for adding new items, [x] for removing items and drag&drop for changing order.'),
    )

    currentEpisode = models.OneToOneField(Episode, blank=True, null=True)

    listener = models.IntegerField(default=0)

    recording = models.BooleanField(default=True, editable=False)
    public_recording = models.BooleanField(default=True, editable=False)

#    agb_accepted = models.BooleanField(default=False, editable=False)
#    agb_accepted_date = models.DateTimeField(auto_now_add=True, editable=False)

    graphic_differ_by = models.CharField(max_length=255, blank=True)

    graphic_title = models.CharField(max_length=255, blank=True)

    def running_streams(self):
        return self.stream_set.filter(running=True).exclude(format="aac")

    def updateRunning(self):
        self.running = False
        for stream in self.stream_set.all():
            if stream.running:
                self.running = True
                break
        self.save()

    def __unicode__(self):
        return _("Channel for %(cluster)s") % {'cluster': self.cluster}

    class Meta:
        permissions = (
            ('change_stream', 'Change Stream'),
        )


class Stream(models.Model):
    """
        a single stream for a episode of a show, which is relayed by different
        Relays
    """

    channel = models.ForeignKey(Channel)

    mount = models.CharField(max_length=80, unique=True)
    running = models.BooleanField(default=False)

    FORMATS = (
        ('mp3', _('MP3')),
        ('aac', _('AAC')),
        ('ogg', _('Ogg/Vorbis')),
        ('ogm', _('Ogg/Theora')),
    )

    format = models.CharField(max_length=100,
        choices=FORMATS, default=FORMATS[0][0])
    BITRATES = (
        ('32', '~32 KBit/s'),
        ('40', '~40 KBit/s'),
        ('48', '~48 KBit/s'),
        ('56', '~56 KBit/s'),
        ('64', '~64 KBit/s'),
        ('72', '~72 KBit/s'),
        ('80', '~80 KBit/s'),
        ('88', '~88 KBit/s'),
        ('96', '~96 KBit/s'),
        ('104', '~104 KBit/s'),
        ('112', '~112 KBit/s'),
        ('120', '~120 KBit/s'),
        ('128', '~128 KBit/s'),
        ('136', '~136 KBit/s'),
        ('144', '~144 KBit/s'),
        ('152', '~152 KBit/s'),
        ('160', '~160 KBit/s'),
        ('168', '~168 KBit/s'),
        ('176', '~176 KBit/s'),
        ('184', '~184 KBit/s'),
        ('192', '~192 KBit/s'),
        ('200', '~200 KBit/s'),
        ('208', '~208 KBit/s'),
        ('216', '~216 KBit/s'),
        ('224', '~224 KBit/s'),
        ('232', '~232 KBit/s'),
        ('240', '~240 KBit/s'),
        ('248', '~248 KBit/s'),
        ('256', '~256 KBit/s'),
    )
    bitrate = models.CharField(max_length=100, choices=BITRATES, default=BITRATES[12][0])

    ENCODINGS = (
        ('UTF-8', _('UTF-8')),
        ('ISO8859-15', _('ISO8859-15')),
    )

    encoding = models.CharField(max_length=255,
        choices=ENCODINGS, default=ENCODINGS[0][0])

    def updateRunning(self):
        self.running = False
        self.save()
        if self.channel_id:
            self.channel.updateRunning()

    def __unicode__(self):
        return unicode("%s at %s at %s" % \
                            (self.format, self.bitrate, self.mount))

    WAVE = (
        ('none', _("No Fallback")),
        ('sine', _("Sine")),
        ('square', _("Square")),
        ('saw', _("Saw")),
        ('triangle', _("Triangle")),
        ('silence', _("Silence")),
        ('white-noise', _("White uniform noise")),
        ('pink-noise', _("Pink noise")),
        ('sine-table', _("Sine table")),
        ('ticks', _("Periodic Ticks")),
        ('gaussian-noise', _("White Gaussian noise")),
    )

    fallback = models.CharField(max_length=255,
        choices=WAVE, default=WAVE[0][0])    


#    def save(self, force_insert=False, force_update=False):
#        super(Stream, self).save(force_insert, force_update)

class SourcedStream(Stream):
    user = models.CharField(max_length=255, blank=True, default="source")
    password = models.CharField(max_length=255, blank=True)

class RecodedStream(Stream):
    source = models.ForeignKey(SourcedStream, related_name='recoded')

class HLSStream(RecodedStream):
    pass
 
class Status(models.Model):
    name = models.CharField(max_length=100)
    status = models.PositiveSmallIntegerField()
    verbose_status = models.CharField(max_length=100)
    timestamp = models.DateTimeField()
    category = models.CharField(max_length=100)
    step = models.PositiveIntegerField()

    def value(self):
        import datetime
        now = datetime.datetime.now()
        diff = now - self.timestamp
        return ((diff.seconds - self.step) * 1.0 / self.step)

    def __unicode__(self):
        return u"<Status for %s>" % self.name

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class Message(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    message_object = generic.GenericForeignKey('content_type', 'object_id')
    timestamp = models.DateTimeField(auto_now_add=True)
    origin = models.CharField(max_length=50)
    message = models.CharField(max_length=255)
    severity = models.PositiveIntegerField(default=3)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['read','-timestamp']

class NotificationPath(models.Model):    
    def get(self):
        if hasattr(self, "twitteraccount"):
            return self.twitteraccount
        elif hasattr(self, "httpcallback"):
            return self.httpcallback
        elif hasattr(self, "ircchannel"):
            return self.ircchannel

    def name(self):
        return self.get().name()

    def __unicode__(self):
        return self.get().__unicode__()


class HTTPCallback(NotificationPath):
    url = models.URLField()

    def name(self):
        return u"http"

    def __unicode__(self):
        return u"HTTP Callback "+self.url


class IRCChannel(NotificationPath):
    url = models.CharField(max_length=250)

    def name(self):
        return u"irc"

    def __unicode__(self):
        return u"IRC Channel "+self.url


class TwitterAccount(NotificationPath):
    screen_name = models.CharField(max_length=250)
    oauth_token = models.CharField(max_length=250)
    oauth_secret = models.CharField(max_length=250)

    def name(self):
        return u"twitter"

    def __unicode__(self):
        return u"Twitter Account "+self.screen_name

class NotificationTemplate(models.Model):
    text = models.CharField(max_length=250)

    def __unicode__(self):
        return self.text

class PrimaryNotification(models.Model):
    path = models.ForeignKey(NotificationPath)
    show = models.ForeignKey(Show)
    start = models.OneToOneField(NotificationTemplate, related_name="start")
    stop = models.OneToOneField(NotificationTemplate, related_name="stop")
    rollover = models.OneToOneField(NotificationTemplate, related_name="rollover")
    system = models.BooleanField(default=False)

    def __unicode__(self):
        return u"Notification for "+unicode(self.show)+" on "+unicode(self.path)

@receiver(post_delete, sender=PrimaryNotification)
def post_delete_user(sender, instance, *args, **kwargs):
    if instance.start:
        instance.start.delete()
    if instance.stop:
        instance.stop.delete()
    if instance.rollover:
        instance.rollover.delete()
    if instance.path and not instance.path.primarynotification_set.all():
        instance.path.delete()

class SecondaryNotification(models.Model):
    path = models.ForeignKey(NotificationPath)
    show = models.ForeignKey(Show)
    primary = models.ForeignKey(PrimaryNotification, blank=True, null=True)

    def __unicode__(self):
        ret = u"Retweet Notification on "+unicode(self.path)
        if self.primary:
            ret += " from "+unicode(self.primary.path)
        return ret
