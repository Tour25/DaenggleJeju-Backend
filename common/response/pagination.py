from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class EnvelopedPageNumberPagination(PageNumberPagination):

    page_size_query_param = "size"
    max_page_size = 100

    def get_paginated_response(self, data):
        meta = {
            "page": self.page.number,
            "size": self.get_page_size(self.request) or self.page.paginator.per_page,
            "totalPages": self.page.paginator.num_pages,
            "totalElements": self.page.paginator.count,
        }

        return Response({"items": data, "page": meta}, status=200)
