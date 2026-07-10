from math import ceil


class Paginator:
    def __init__(self, total: int, page: int = 1, per_page: int = 20):
        self.total = total
        self.page = max(1, page)
        self.per_page = min(100, max(1, per_page))
        self.total_pages = ceil(total / self.per_page) if total > 0 else 1
        self.offset = (self.page - 1) * self.per_page
        self.has_next = self.page < self.total_pages
        self.has_prev = self.page > 1

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }
