// d = b * b - 4 * a * c

// if d > 0:
//     x1 = (-b + sqrt(d)) / (2 * a)
//     x2 = (-b - sqrt(d)) / (2 * a)

// else:
//     re = -b / (2 * a)
//     im = sqrt(d) / (2 * a)
//     x1 = re, im
//     x2 = re, -im

d = b * b - 4 * a * c

x1 = (-b + sqrt(d)) / (2 * a)
x2 = (-b - sqrt(d)) / (2 * a)
x3 = (+b + sqrt(d)) / (2 * a)