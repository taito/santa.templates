from Acquisition import aq_parent
from OFS.interfaces import IItem
from Products.ATContentTypes.interfaces.document import IATDocument
from Products.ATContentTypes.interfaces.event import IATEvent
from Products.ATContentTypes.interfaces.image import IATImage
from Products.ATContentTypes.interfaces.news import IATNewsItem
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot
from five import grok
from plone.app.contentlisting.interfaces import IContentListing
from plone.app.layout.viewlets.interfaces import IPortalHeader
from plone.app.viewletmanager.manager import OrderedViewletManager
from santa.content.partner import IPartner
from santa.templates.browser.interfaces import ISantaTemplatesLayer
from zope.component import getMultiAdapter
from plone.namedfile.file import NamedImage

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
        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
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


class SantaTopViewletManager(OrderedViewletManager, grok.ViewletManager):
    """Viewlet manager to Santa Top."""
    grok.context(IPloneSiteRoot)
    grok.layer(ISantaTemplatesLayer)
    grok.name('santa.top.manager')


class BaseViewlet(grok.Viewlet):
    """Base Viewlet Class."""
    grok.baseclass()
    grok.context(IPloneSiteRoot)
    grok.layer(ISantaTemplatesLayer)
    grok.require('zope2.View')
    grok.viewletmanager(SantaTopViewletManager)


class AboutViewlet(BaseViewlet):
    grok.name('santa.viewlet.about')
    grok.template('about')

    def item(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
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
        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
        portal = portal_state.portal()
        item = portal.get('inquiries')
        if item:
            query = {
                'path': {
                    'query': '/'.join(item.getPhysicalPath()),
                    'depth': 1,
                }
            }
            return IContentListing(catalog(query))


class FeedViewlet(BaseViewlet):
    grok.baseclass()
    name = 'feed'
    grok.template(name)

    oid = ''

    def parent_path(self):
        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
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

    def getItems(
        self,
        interface=IATDocument,
        limit=1,
        sort_on="modified",
        depth=1
    ):
        catalog = getToolByName(self.context, 'portal_catalog')
        path = self.parent_path()
        if depth:
            path = {
                'query': path,
                'depth': depth,
            }
        query = {
            'path': path,
            'object_provides': interface.__identifier__,
            'sort_limit': limit,
            'sort_on': sort_on,
            'sort_order': 'descending',
        }
        ploneview = getMultiAdapter(
            (self.context, self.request),
            name=u'plone'
        )
        return  [
            {
                'title': item.Title(),
                'url': item.getURL(),
                'description': item.Description(),
                'date': self.date(item, sort_on),
                # 'start': ploneview.toLocalizedTime(item.start) if item.start is not Missing.Value else None,
                'end': ploneview.toLocalizedTime(item.end, long_format=True) if item.end is not Missing.Value else None,
                'image': self.image(item),
            } for item in IContentListing(catalog(query)[:limit])
        ]

    def date(self, item, sort_on):
        ploneview = getMultiAdapter(
            (self.context, self.request),
            name=u'plone'
        )
        if sort_on == 'modified':
            return ploneview.toLocalizedTime(item.ModificationDate())
        else:
            return ploneview.toLocalizedTime(getattr(item, sort_on), long_format=True)

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
        return self.getItems(interface=IATNewsItem)


class EventsViewlet(FeedViewlet):
    grok.name('santa.viewlet.events')
    oid = 'events'

    def items(self):
        return self.getItems(interface=IATEvent, sort_on='start')


class PartnersViewlet(FeedViewlet):
    grok.name('santa.viewlet.partners')
    oid = 'partners'

    def items(self):
        return self.getItems(interface=IPartner)


class CasesViewlet(FeedViewlet):
    grok.name('santa.viewlet.cases')
    oid = 'partners'

    def items(self):
        return self.getItems(interface=IATImage, depth=None)

    def _path(self):
        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
        portal = portal_state.portal()
        return '{0}/cases'.format(
            '/'.join(portal.getPhysicalPath()),
        )
