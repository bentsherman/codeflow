from math import sqrt

def quadratic(a, b, c):
    d = b ** 2 - 4 * a * c
    re = -b / (2 * a)
    im = sqrt(d) / (2 * a)

    if d > 0:
        x1 = re + im
        x2 = re - im
    else:
        x1 = (re, im)
        x2 = (re, -im)

    return x1, x2

x1, x2 = quadratic(1, 2, 3)
