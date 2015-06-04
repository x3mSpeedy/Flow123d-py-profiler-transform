# encoding: utf-8
# author:   Jan Hybs
from markdown import markdown
from ist.utils.texlist import texlist
import xml.etree.ElementTree as ET


class Html2Latex (object):
    list_types = {
        'ul': 'itemize',
        'ol': 'enumerate'
    }

    def __init__ (self, element):
        if type (element) is str:
            tree = ET.fromstring ('<html_example>' + element + "</html_example>")
            self.el = tree
        else:
            self.el = element
        self.tex = texlist ()

    def extend_children (self):
        for child in self.el:
            self.tex.extend (Html2Latex (child).to_latex ())

    def tag_is (self, *tags):
        return self.el.tag in tags

    def text (self):
        return self.el.text if self.el.text else ''

    def tail (self):
        return self.el.tail if self.el.tail else ''

    def add_tail (self):
        self.tex.append (self.tail ())

    def get_list_type (self):
        return self.list_types.get (self.el.tag, 'itemize')

    #
    # def tag (self):
    # return self.el.tag

    def to_latex (self):


        if self.tag_is ('p'):
            with self.tex:
                self.tex.append (self.text ())
                self.extend_children ()
            self.add_tail ()
            self.tex.newline ()

        elif self.tag_is ('h1'):
            self.tex.append ('\\section')
            with self.tex:
                self.tex.append (self.text ())
                self.extend_children ()
            self.add_tail ()

        elif self.tag_is ('a'):
            self.tex.extend (LatexHref (self.el).to_latex ())

        elif self.tag_is ('em'):
            self.tex.append ('\\textit')
            with self.tex:
                self.tex.append (self.text ())
                self.extend_children ()
            self.add_tail ()

        elif self.tag_is ('strong'):
            self.tex.append ('\\textbf')
            with self.tex:
                self.tex.append (self.text ())
                self.extend_children ()
            self.add_tail ()

        elif self.tag_is ('ul', 'ol'):
            self.tex.open_element (self.get_list_type ())
            self.tex.append (self.text ())
            self.extend_children ()
            self.tex.close_element (self.get_list_type ())
            self.add_tail ()

        elif self.tag_is ('li'):
            with self.tex:
                self.tex.append ('\\item ')
                self.tex.append (self.text ())
                self.extend_children ()
            self.add_tail ()


        elif self.tag_is ('code'):
            self.tex.open_element ('lstlisting')
            self.tex.newline ()
            self.tex.append (self.text ())
            self.extend_children ()
            self.tex.newline ()
            self.tex.close_element ('lstlisting')
            self.add_tail ()

        elif self.tag_is ('span'):
            self.tex.append (self.text ())
            self.extend_children ()
            self.add_tail ()

        else:
            with self.tex:
                self.tex.append (self.text ())
                self.extend_children ()
                self.add_tail ()

        return self.tex


class LatexHref (Html2Latex):
    def to_latex (self):

        # Alink href?
        if self.el.attrib.get ('data-href') == 'Alink':
            url = self.el.attrib.get('href')
            ns = self.el.attrib.get('data-ns')
            text = self.text()
            self.tex.Alink(url=url, ns=ns, text=text)
            self.add_tail ()
        else:
        # other href
            self.tex.append ('\\href')
            self.tex.add (self.el.attrib.get ('href'))
            with self.tex:
                self.tex.add (self.text ())
                self.extend_children ()
            self.add_tail ()
        return self.tex
