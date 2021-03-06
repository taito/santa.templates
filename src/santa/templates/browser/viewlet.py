from Acquisition import aq_parent
from DateTime import DateTime
from OFS.interfaces import IItem
from Products.ATContentTypes.interfaces.document import IATDocument
from Products.ATContentTypes.interfaces.event import IATEvent
from Products.ATContentTypes.interfaces.folder import IATFolder
from Products.ATContentTypes.interfaces.image import IATImage
from Products.ATContentTypes.interfaces.news import IATNewsItem
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.PloneFormGen.interfaces import IPloneFormGenForm
from five import grok
from plone.app.contentlisting.interfaces import IContentListing
from plone.app.layout.viewlets.interfaces import IBelowContent
from plone.app.layout.viewlets.interfaces import IBelowContentBody
from plone.app.layout.viewlets.interfaces import IPortalHeader
from plone.app.viewletmanager.manager import OrderedViewletManager
from plone.namedfile.file import NamedImage
from santa.content.partner import IPartner
from santa.templates import _
from santa.templates.browser.interfaces import ISantaTemplatesLayer
from zope.component import getMultiAdapter

import Missing


grok.templatedir('viewlets')


class HeadTitleViewlet(grok.Viewlet):
    grok.context(IItem)
    grok.layer(ISantaTemplatesLayer)
    grok.name('santa.head.title')
    grok.require('zope2.View')
    grok.template('head-title')
    grok.viewletmanager(IPortalHeader)

    def head(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        portal_state = getMultiAdapter(
            (self.context, self.request),
            name="plone_portal_state"
        )
        portal = portal_state.portal()
        items = {
            'title': portal.title,
            'description': portal.description,
            'portal_url': portal.absolute_url(),
        }
        head = portal.get('foundation')
        if head:
            query = {
                'path': {
                    'query': '/'.join(head.getPhysicalPath()),
                    'depth': 1
                }
            }
            brains = catalog(query)
            if len(brains) > 0:
                brain = brains[0]
                title = brain.Title
                description = brain.Description
                if title:
                    items.update({'title': title})
                if description:
                    items.update({'description': description})
        return items


class SantaFolderViewletManager(OrderedViewletManager, grok.ViewletManager):
    """Viewlet manager to Folder."""
    grok.context(IATFolder)
    grok.layer(ISantaTemplatesLayer)
    grok.name('santa.folder.manager')


class SantaTopViewletManager(OrderedViewletManager, grok.ViewletManager):
    """Viewlet manager to Santa Top."""
    grok.context(IPloneSiteRoot)
    grok.layer(ISantaTemplatesLayer)
    grok.name('santa.top.manager')


class BaseViewlet(grok.Viewlet):
    """Base Viewlet Class."""
    grok.baseclass()
    grok.context(IItem)
    grok.layer(ISantaTemplatesLayer)
    grok.require('zope2.View')
    grok.viewletmanager(SantaTopViewletManager)


class AboutViewlet(BaseViewlet):
    grok.name('santa.viewlet.about')
    grok.template('about')

    def item(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        portal_state = getMultiAdapter(
            (self.context, self.request),
            name="plone_portal_state"
        )
        portal = portal_state.portal()
        item = portal.get('foundation')
        if item:
            query = {
                'path': {
                    'query': '/'.join(item.getPhysicalPath()),
                    'depth': 1,
                }
            }
            brains = catalog(query)
            if brains:
                brain = brains[0]
                obj = brain.getObject()
                return {
                    'description': brain.Description,
                    'text': obj.getField('text').get(obj),
                    'title': brain.Title,
                    'url': aq_parent(obj).absolute_url(),
                }

    def inquiries(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        portal_state = getMultiAdapter(
            (self.context, self.request),
            name="plone_portal_state"
        )
        portal = portal_state.portal()
        item = portal.get('inquiries')
        if item:
            query = {
                'path': {
                    'query': '/'.join(item.getPhysicalPath()),
                    'depth': 1,
                },
                'object_provides': IPloneFormGenForm.__identifier__,
            }
            return IContentListing(catalog(query))


class FeedViewlet(BaseViewlet):
    grok.baseclass()
    name = 'feed'
    grok.template(name)

    oid = ''

    def has_date(self):
        return True

    def show_description(self):
        return False

    def parent_path(self):
        portal_state = getMultiAdapter(
            (self.context, self.request),
            name="plone_portal_state"
        )
        portal = portal_state.portal()
        return '{0}/{1}'.format(
            '/'.join(portal.getPhysicalPath()),
            self.oid,
        )

    def _path(self):
        return self.parent_path()

    def parent(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'path': {
                'query': self._path(),
                'depth': 0,
            }
        }
        brains = catalog(query)
        if brains:
            return brains[0]

    def id(self):
        parent = self.parent()
        return parent and parent.id

    def title(self):
        parent = self.parent()
        return parent and parent.Title

    def description(self):
        parent = self.parent()
        return parent and parent.Description

    def url(self):
        parent = self.parent()
        return parent and parent.getURL()

    def text(self):
        return None

    def _brains(
        self,
        interface=IATDocument,
        sort_on="modified",
        path=None,
        depth=1,
        limit=0,
    ):
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'object_provides': interface.__identifier__,
            'sort_on': sort_on,
            'sort_order': 'descending',
        }
        if path:
            if depth:
                path = {
                    'query': path,
                    'depth': depth,
                }
            query.update({'path': path})
        if limit:
            query.update({'sort_limit': limit})
            return catalog(query)[:limit]
        return catalog(query)

    def _items(self, brains):
        return  [
            {
                'title': item.Title(),
                'url': item.getURL(),
                'description': item.Description(),
                'date': self._date(item),
                'end': self._end(item),
                'image': self.image(item),
            } for item in IContentListing(brains)
        ]

    def items(self):
        return True

    def show_docs(self):
        return self.items()

    def _date(self, item):
        ploneview = getMultiAdapter(
            (self.context, self.request),
            name=u'plone'
        )
        if item.start is not Missing.Value:
            return ploneview.toLocalizedTime(item.start, long_format=True)
        else:
            return ploneview.toLocalizedTime(item.ModificationDate())

    def _end(self, item):
        ploneview = getMultiAdapter(
            (self.context, self.request),
            name=u'plone'
        )
        if item.end is not Missing.Value:
            return ploneview.toLocalizedTime(item.end, long_format=True)

    def image(self, item):
        portal_state = getMultiAdapter(
            (self.context, self.request),
            name=u'plone_portal_state'
        )
        image_url = '{0}/++resource++santa.templates.images/{1}-fallback.png'.format(
            portal_state.portal_url(),
            self.name
        )
        html = '<img class="santa-fall-back" src="{0}" alt="{1}" title="{2}" />'.format(
            image_url,
            item.Description(),
            item.Title(),
        )
        obj = item.getObject()
        field_name = 'image' if (
            obj.getField('image') or hasattr(obj, 'image')
        ) else 'leadImage'
        field = obj.getField(field_name) or getattr(obj, field_name)
        isins = isinstance(field, NamedImage)
        if (
            field and not isins and field.get(obj)
        ) or isins:
            html = obj.restrictedTraverse('images').tag(field_name, scale='mini')
        return html


class NewsViewlet(FeedViewlet):
    grok.name('santa.viewlet.news')
    oid = 'news'

    def items(self):
        brains = self._brains(interface=IATNewsItem, limit=1)
        return self._items(brains)


class ComingEventsViewlet(FeedViewlet):
    grok.name('santa.viewlet.comingevents')
    oid = 'events'

    def title(self):
        return _(u'Coming Events')

    def items(self):
        brains = [
            brain for brain in self._brains(
                interface=IATEvent, sort_on='start'
            ) if brain.start > DateTime()
        ]
        return self._items(brains[-1:])


class LatestEventsViewlet(FeedViewlet):
    grok.name('santa.viewlet.latestevents')
    oid = 'events'

    def title(self):
        return _(u'Latest Events')

    def items(self):
        brains = [
            brain for brain in self._brains(
                interface=IATEvent, sort_on='start'
            ) if brain.start < DateTime()
        ]
        return self._items(brains[:1])


class PartnersViewlet(FeedViewlet):
    grok.name('santa.viewlet.partners')
    oid = 'partners'

    def items(self):
        brains = self._brains(interface=IPartner, limit=1)
        return self._items(brains)


class CasesViewlet(FeedViewlet):
    grok.name('santa.viewlet.cases')
    oid = 'partners'

    def items(self):
        brains = self._brains(interface=IATImage, path=self.parent_path(), depth=None, limit=1)
        return self._items(brains)

    def _path(self):
        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
        portal = portal_state.portal()
        return '{0}/cases'.format(
            '/'.join(portal.getPhysicalPath()),
        )


class FolderViewlet(FeedViewlet):
    grok.name('santa.viewlet.folder')
    grok.viewletmanager(SantaFolderViewletManager)

    def parent_path(self):
        oid = self.context.id
        if oid == 'cases':
            oid = 'partners'
        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
        portal = portal_state.portal()
        return '{0}/{1}'.format(
            '/'.join(portal.getPhysicalPath()),
            oid,
        )

    def _path(self):
        oid = self.context.id
        if oid == 'cases':
            portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
            portal = portal_state.portal()
            return '{0}/cases'.format(
                '/'.join(portal.getPhysicalPath()),
            )
        else:
            return super(FolderViewlet, self)._path()

    def has_date(self):
        oid = self.context.id
        if oid != 'inquiries':
            return True

    def items(self):
        oid = self.context.id
        limit = 5
        if oid == 'news':
            brains = self._brains(interface=IATNewsItem, limit=limit)
        if oid == 'events':
            brains = self._brains(interface=IATEvent, sort_on='start', limit=limit)
        if oid == 'partners':
            brains = self._brains(interface=IPartner, limit=limit)
        if oid == 'cases':
            brains = self._brains(interface=IATImage, path=self.parent_path(), depth=None, limit=limit)
        if oid == 'inquiries':
            brains = self._brains(interface=IPloneFormGenForm, sort_on=None, limit=None)
        if oid == 'foundation':
            return None
        return self._items(brains)

    def show_docs(self):
        oid = self.context.id
        if oid == 'foundation':
            return True
        return super(FolderViewlet, self).show_docs()

    def show_description(self):
        oid = self.context.id
        if oid == 'foundation':
            return True

    def _document(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        languages = getToolByName(self.context, 'portal_languages')
        oids = languages.supported_langs
        query = {
            'path': {
                'query': '/'.join(self.context.getPhysicalPath()),
                'depth': 1,
            },
            'object_provides': IATDocument.__identifier__,
        }
        brains = catalog(query)
        if brains:
            brain = brains[0]
            bid = brain.id
            if bid in oids:
                return brain

    def title(self):
        doc = self._document()
        return doc and doc.Title or self.context.Title()

    def description(self):
        doc = self._document()
        return doc and doc.Description or self.context.Description()

    def url(self):
        return self.context.absolute_url()

    def text(self):
        doc = self._document()
        if doc:
            obj = doc.getObject()
            return obj.getField('text').get(obj)


class EventListingViewlet(BaseViewlet):
    """Viewlet to show event listing."""
    grok.context(IPloneSiteRoot)
    grok.name('santa.templates.event.listing')
    grok.template('event-listing')
    grok.viewletmanager(IBelowContentBody)

    def events(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'object_provides': IATEvent.__identifier__,
        }
