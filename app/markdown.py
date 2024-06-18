import re


def markdown(input):
    lines = input.splitlines()
    output = []
    md = Markdown(output)
    md.render(lines)
    return output


class Markdown:
    def __init__(self, out=[]):
        self.out = out
        self.block = ""
        self.typ = None

    def render_block(self, typ, block):
        if not block:
            return

        def tt(m):
            return "<tt>" + m.group(1).replace("<", "&lt;") + "</tt>"

        block = re.sub("`(.+?)`", tt, block)
        block = re.sub("\*\*(.+?)\*\*", "<b>\\1</b>", block)
        block = re.sub("\*(.+?)\*", "<i>\\1</i>", block)
        block = re.sub("~~(.+)~~", "<strike>\\1</strike>", block)
        # block = re.sub("!\[(.+?)\]\((.+?)\)", '<img src="\\2" alt="\\1">', block)
        block = re.sub("\[(.+?)\]\((.+?)\)", '<a href="\\2">\\1</a>', block)

        if typ == "list":
            tag = "li"
        elif typ == "bquote":
            tag = "blockquote"
        else:
            tag = "p"

        self.out.append(f"<{tag}>")
        self.out.append(block)
        self.out.append(f"</{tag}>")

    def flush_block(self):
        self.render_block(self.typ, self.block)
        self.block = ""
        self.typ = None

    def render_line(self, line):
        l_strip = line.rstrip()
        # print(l_strip)

        # Handle pre block content/end
        if self.typ == "```" or self.typ == "~~~":
            if l_strip == self.typ:
                self.typ = None
                self.out.append("</pre>")
            else:
                self.out.append(line)
            return

        # Handle pre block start
        if line.startswith("```") or line.startswith("~~~"):
            self.flush_block()
            self.typ = line[0:3]
            self.out.append("<pre>")
            return

        # Empty line ends current block
        if not l_strip and self.block:
            self.flush_block()
            return

        # Repeating empty lines are ignored - TODO
        if not l_strip:
            return

        # Handle heading
        if line.startswith("#"):
            self.flush_block()
            level = 0
            while line.startswith("#"):
                line = line[1:]
                level += 1
            line = line.strip()
            level = 4  # overwrite heading
            self.out.append("<h%d>%s</h%d>" % (level, line, level))
            return

        if line.startswith("> "):
            if self.typ != "bquote":
                self.flush_block()
            self.typ = "bquote"
            line = line[2:]
        elif line.startswith("* "):
            self.flush_block()
            self.typ = "list"
            line = line[2:]

        if not self.typ:
            self.typ = "para"

        self.block += line

    def render(self, lines):
        for line in lines:
            self.render_line(line)

        # Render trailing block
        self.flush_block()
