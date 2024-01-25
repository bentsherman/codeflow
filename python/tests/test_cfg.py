
import codeflow.cfg as cfg



test_pass = (
"""
pass
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label=pass, peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label=stop, peripheries=2, shape=oval];
1 -> 2  [color=black];
}
"""
)



test_expr = (
"""
10
'a'
10 + 1
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label=stop, peripheries=2, shape=oval];
0 -> 1  [color=black];
}
"""
)



test_assign = (
"""
a = 10 + 1
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="a = (10 + 1)", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label=stop, peripheries=2, shape=oval];
1 -> 2  [color=black];
}
"""
)



test_if = (
"""
a = 1
if a > 1:
    a = 1
else:
    a = 0
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="a = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="if (a > 1)", peripheries=1, shape=diamond];
1 -> 2  [color=black];
4 [label="a = 1", peripheries=1, shape=rectangle];
2 -> 4  [color=blue];
6 [label="a = 0", peripheries=1, shape=rectangle];
2 -> 6  [color=red];
7 [label=stop, peripheries=2, shape=oval];
4 -> 7  [color=black];
6 -> 7  [color=black];
}
"""
)



test_while = (
"""
x = 1
while x > 0:
    x = x - 1
y = x
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="x = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="while (x > 0)", peripheries=1, shape=diamond];
1 -> 2  [color=black];
5 -> 2  [color=black];
5 [label="x = (x - 1)", peripheries=1, shape=rectangle];
2 -> 5  [color=blue];
6 [label="y = x", peripheries=1, shape=rectangle];
2 -> 6  [color=red];
7 [label=stop, peripheries=2, shape=oval];
6 -> 7  [color=black];
}
"""
)



test_while_break = (
"""
x = 1
while x > 0:
    if x > 1:
        break
    x = x - 1
y = x
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="x = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="while (x > 0)", peripheries=1, shape=diamond];
1 -> 2  [color=black];
9 -> 2  [color=black];
5 [label="if (x > 1)", peripheries=1, shape=diamond];
2 -> 5  [color=blue];
7 [label=break, peripheries=1, shape=rectangle];
5 -> 7  [color=blue];
9 [label="x = (x - 1)", peripheries=1, shape=rectangle];
5 -> 9  [color=red];
10 [label="y = x", peripheries=1, shape=rectangle];
2 -> 10  [color=red];
7 -> 10  [color=black];
11 [label=stop, peripheries=2, shape=oval];
10 -> 11  [color=black];
}
"""
)



test_while_continue = (
"""
x = 1
while x > 0:
    if x > 1:
        continue
    x = x - 1
y = x
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="x = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="while (x > 0)", peripheries=1, shape=diamond];
1 -> 2  [color=black];
9 -> 2  [color=black];
7 -> 2  [color=black];
5 [label="if (x > 1)", peripheries=1, shape=diamond];
2 -> 5  [color=blue];
7 [label=continue, peripheries=1, shape=rectangle];
5 -> 7  [color=blue];
9 [label="x = (x - 1)", peripheries=1, shape=rectangle];
5 -> 9  [color=red];
10 [label="y = x", peripheries=1, shape=rectangle];
2 -> 10  [color=red];
11 [label=stop, peripheries=2, shape=oval];
10 -> 11  [color=black];
}
"""
)



test_for = (
"""
x = 1
for i in vals:
    x = x - 1
y = x
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="x = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="for i in vals", peripheries=1, shape=diamond];
1 -> 2  [color=black];
5 -> 2  [color=black];
5 [label="x = (x - 1)", peripheries=1, shape=rectangle];
2 -> 5  [color=blue];
6 [label="y = x", peripheries=1, shape=rectangle];
2 -> 6  [color=red];
7 [label=stop, peripheries=2, shape=oval];
6 -> 7  [color=black];
}
"""
)



test_for_break = (
"""
x = 1
for i in vals:
    if x > 1:
        break
    x = x - 1
y = x
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="x = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="for i in vals", peripheries=1, shape=diamond];
1 -> 2  [color=black];
9 -> 2  [color=black];
5 [label="if (x > 1)", peripheries=1, shape=diamond];
2 -> 5  [color=blue];
7 [label=break, peripheries=1, shape=rectangle];
5 -> 7  [color=blue];
9 [label="x = (x - 1)", peripheries=1, shape=rectangle];
5 -> 9  [color=red];
10 [label="y = x", peripheries=1, shape=rectangle];
2 -> 10  [color=red];
7 -> 10  [color=black];
11 [label=stop, peripheries=2, shape=oval];
10 -> 11  [color=black];
}
"""
)



test_for_continue = (
"""
x = 1
for i in vals:
    if x > 1:
        continue
    x = x - 1
y = x
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="x = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="for i in vals", peripheries=1, shape=diamond];
1 -> 2  [color=black];
9 -> 2  [color=black];
7 -> 2  [color=black];
5 [label="if (x > 1)", peripheries=1, shape=diamond];
2 -> 5  [color=blue];
7 [label=continue, peripheries=1, shape=rectangle];
5 -> 7  [color=blue];
9 [label="x = (x - 1)", peripheries=1, shape=rectangle];
5 -> 9  [color=red];
10 [label="y = x", peripheries=1, shape=rectangle];
2 -> 10  [color=red];
11 [label=stop, peripheries=2, shape=oval];
10 -> 11  [color=black];
}
"""
)



test_functiondef = (
"""
x = 1
def my_fn(v1, v2):
    if v1 > v2:
        return v1
    else:
        return v2
y = 2
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="x = 1", peripheries=1, shape=rectangle];
0 -> 1  [color=black];
2 [label="def my_fn(v1, v2)", peripheries=2, shape=oval];
3 [label="if (v1 > v2)", peripheries=1, shape=diamond];
2 -> 3  [color=black];
5 [label="return v1", peripheries=1, shape=rectangle];
3 -> 5  [color=blue];
7 [label="return v2", peripheries=1, shape=rectangle];
3 -> 7  [color=red];
8 [label="y = 2", peripheries=1, shape=rectangle];
1 -> 8  [color=black];
9 [label=stop, peripheries=2, shape=oval];
8 -> 9  [color=black];
}
"""
)



test_call = (
"""
def my_fn(v1, v2):
    if v1 > v2:
        return v1
    else:
        return v2

my_fn(2, 1)
my_fn(3, 4)
""",

"""
digraph G {
0 [label=start, peripheries=2, shape=oval];
1 [label="def my_fn(v1, v2)", peripheries=2, shape=oval];
2 [label="if (v1 > v2)", peripheries=1, shape=diamond];
1 -> 2  [color=black];
4 [label="return v1", peripheries=1, shape=rectangle];
2 -> 4  [color=blue];
6 [label="return v2", peripheries=1, shape=rectangle];
2 -> 6  [color=red];
7 [label="my_fn(2, 1)", peripheries=1, shape=rectangle];
0 -> 7  [color=black];
8 [label="my_fn(3, 4)", peripheries=1, shape=rectangle];
7 -> 8  [color=black];
9 [label=stop, peripheries=2, shape=oval];
8 -> 9  [color=black];
}
"""
)



def test():
    tests = [
        test_pass,
        test_expr,
        test_assign,
        test_if,
        test_while,
        test_while_break,
        test_while_continue,
        test_for,
        test_for_break,
        test_for_continue,
        test_functiondef,
        test_call
    ]

    for source_text, dot_graph in tests:
        G_dot = cfg.ControlFlowGraph().generate(source_text).to_dot()
        assert G_dot.to_string() == dot_graph.lstrip()
