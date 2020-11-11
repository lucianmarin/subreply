from collections import Sequence


class Paginate(Sequence):
    def __init__(self, request, query, limit=3):
        self.query = query
        self.limit = limit
        try:
            self.page = abs(int(request.params.get('p', 1)))
            self.page = 1 if self.page == 0 else self.page
        except ValueError:
            self.page = 1

    def __len__(self):
        return len(self.list)

    # def __getitem__(self, index):
    #     if not isinstance(index, (int, slice)):
    #         raise TypeError
    #     return self.list[index]

    @property
    def count(self):
        if self.page != 1 or len(self.list) == self.limit:
            return self.query.count()
        else:
            return len(self.list)

    @property
    def has_next(self):
        return len(self.sliced) == self.limit + 1

    @property
    def has_previous(self):
        return self.page != 1

    @property
    def sliced(self):
        bottom = (self.page - 1) * self.limit
        top = bottom + self.limit + 1
        return list(self.query[bottom:top])

    @property
    def list(self):
        return self.sliced[:self.limit]
