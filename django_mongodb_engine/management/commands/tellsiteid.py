from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Tells the ID of the default Site object."

    def handle_noargs(self, **options):
        verbosity = int(options.get('verbosity', 1))
        site_id = self._get_site_id()
        if verbosity >= 1:
            self.stdout.write(
                "The default site's ID is %r. To use the sites framework, "
                "add this line to settings.py:\nSITE_ID=%r" %
                (site_id, site_id))
        else:
            self.stdout.write(site_id)

    def _get_site_id(self):
        from django.contrib.sites.models import Site
        return Site.objects.get().id
