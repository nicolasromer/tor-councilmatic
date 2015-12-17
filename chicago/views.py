from django.shortcuts import render
from datetime import date, timedelta
from chicago.models import ChicagoBill
from councilmatic_core.models import Event
from councilmatic_core.views import *


class ChicagoIndexView(IndexView):
    template_name = 'chicago/index.html'
    bill_model = ChicagoBill

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        
        recently_passed = []
        # go back in time at 10-day intervals til you find 3 passed bills
        for i in range(0,-100, -10):
            begin = date.today() + timedelta(days=i)
            end = date.today() + timedelta(days=i-10)

            leg_in_range = self.bill_model.objects\
                                 .exclude(last_action_date=None)\
                                 .filter(last_action_date__lte=begin)\
                                 .filter(last_action_date__gt=end)\
                                 .order_by('-last_action_date')
            passed_in_range = [l for l in leg_in_range \
                               if l.inferred_status == 'Passed']

            recently_passed.extend(passed_in_range)
            if len(recently_passed) >= 3:
                recently_passed = recently_passed[:3]
                break

        upcoming_meetings = list(self.event_model.upcoming_committee_meetings())

        recent_activity = {}
        date_cutoff = Event.most_recent_past_city_council_meeting().start_time

        new_bills = ChicagoBill.new_bills_since(date_cutoff)
        recent_activity['new'] = new_bills
        recent_activity['new_routine'] = [b for b in new_bills if 'Routine' in b.topics]
        recent_activity['new_nonroutine'] = [b for b in new_bills if 'Non-Routine' in b.topics]
        
        updated_bills = ChicagoBill.updated_bills_since(date_cutoff)
        recent_activity['updated_routine'] = [b for b in updated_bills if 'Routine' in b.topics]
        recent_activity['updated_nonroutine'] = [b for b in updated_bills if 'Non-Routine' in b.topics]

        return {
            'recent_activity': recent_activity,
            'recently_passed': recently_passed,
            'last_council_meeting': Event.most_recent_past_city_council_meeting(),
            'next_council_meeting': Event.next_city_council_meeting(),
            'upcoming_committee_meetings': upcoming_meetings,
        }

class ChicagoAboutView(AboutView):
    template_name = 'chicago/about.html'

# this is for handling bill detail urls from the old chicago councilmatuc
def bill_detail_redirect(request, old_id):
    pattern = '?ID=%s&GUID' %old_id

    try:
        obj = ChicagoBill.objects.get(source_url__contains=pattern)
    except:
        raise Http404("No bill found matching the query")

    return redirect('bill_detail', slug=obj.slug)


class ChicagoBillDetailView(BillDetailView):
    model = ChicagoBill

    def get_object(self, queryset=None):
        """
        Returns a bill based on slug. If no bill found,
        looks for bills based on legistar id (so that
        urls from old Chicago councilmatic don't break)
        """

        if queryset is None:
            queryset = self.get_queryset()

        slug = self.kwargs.get(self.slug_url_kwarg)
        if slug is None:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)

        # Try looking up by slug
        if slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("No bill found matching the query")

        return obj