def quadratic(a, b, c) {
  def d = b * b - 4 * a * c
  def re = -b / (2 * a)
  def im = sqrt(d) / (2 * a)

  def x = d > 0
    ? [re + im, re - im]
    : [[re, im], [re, -im]]

  return x
}

x = quadratic(1, 2, 3)
