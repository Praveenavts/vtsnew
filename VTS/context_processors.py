from .models import CompanyLink

def company_links(request):
    def fix_url(link):
        if link and not link.startswith("http"):
            return f"https://{link}"
        return link or "#"

    vis = CompanyLink.objects.filter(name__icontains="VIS").first()
    vcs = CompanyLink.objects.filter(name__icontains="VCS").first()

    return {
        "vis_link": fix_url(vis.url if vis else None),
        "vcs_link": fix_url(vcs.url if vcs else None),
    }


from .models import Contactnumber

def contact_numbers(request):
    return {
        'footer_numbers': Contactnumber.objects.all()
    }