def get_pagination(page, total, neighbours_number):
    arrow_block_len = neighbours_number * 2 + 3
    pagination_len = arrow_block_len + 2
    if pagination_len >= total:
        return list(range(1, total + 1))

    start_page = max(2, page - neighbours_number)
    end_page = min(total - 1, page + neighbours_number)
    pages = list(range(start_page, end_page + 1))
    to_fill = arrow_block_len - len(pages) - 1

    if start_page > 2 and total - end_page > 1:
        pages = ['&laquo;'] + pages + ['&raquo;']
    elif start_page > 2:
        pages = ['&laquo;'] + list(range(start_page - to_fill, start_page)) + pages
    else:
        pages = pages + list(range(end_page + 1, end_page + to_fill + 1)) + ['&raquo;']

    return [1] + pages + [total]