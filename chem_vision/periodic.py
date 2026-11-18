"""Bảng tra nguyên tố ngoài bộ thẻ in sẵn: gõ tên (hoặc kí hiệu) là có kí hiệu, nguyên tử khối và hóa trị.

Nguyên tử khối làm tròn theo sách giáo khoa THCS; hóa trị đầu tiên là phổ biến nhất. Khí hiếm có hóa trị 0.
Bảng phủ đủ 118 nguyên tố (gõ tên tiếng Việt, tiếng Anh hoặc kí hiệu); không gặp tên nào thì người dùng tự nhập kí hiệu và hóa trị.
"""
from __future__ import annotations

import unicodedata

from .curriculum import ATOMIC_MASS, ELEMENT_NAMES, VALENCE

# Mỗi dòng: kí hiệu | tên tiếng Việt | tên tiếng Anh | nguyên tử khối | hóa trị (phổ biến nhất trước).
# Chỉ để tra khi người dùng thêm nguyên tố: không tự thêm nguyên tố nào vào ứng dụng. Hóa trị của các nguyên tố
# từ Mt (109) trở đi là dự đoán lí thuyết vì chưa có số liệu thực nghiệm.
_TABLE = """
He|heli|helium|4|0
Be|beri|beryllium|9|2
B|bo|boron|11|3
Ne|neon|neon|20|0
Ar|agon|argon|40|0
Sc|scandi|scandium|45|3
Ti|titan|titanium|48|4
V|vanađi|vanadium|51|5,4
Cr|crom|chromium|52|3,2,6
Mn|mangan|manganese|55|2,4,7,6
Co|coban|cobalt|59|2,3
Ni|niken|nickel|59|2
Ga|gali|gallium|70|3
Ge|gecmani|germanium|73|4
As|asen|arsenic|75|3,5
Se|selen|selenium|79|2,4,6
Kr|kripton|krypton|84|0
Rb|rubidi|rubidium|85.5|1
Sr|stronti|strontium|88|2
Y|itri|yttrium|89|3
Zr|zirconi|zirconium|91|4
Nb|niobi|niobium|93|5,3
Mo|molipđen|molybdenum|96|6
Tc|tecneti|technetium|98|7,4
Ru|rutheni|ruthenium|101|3,4,8
Rh|rođi|rhodium|103|3
Pd|paladi|palladium|106|2
Cd|cađimi|cadmium|112|2
In|indi|indium|115|3
Sn|thiếc|tin|119|2,4
Sb|antimon|antimony|122|3,5
Te|telu|tellurium|128|2,4,6
Xe|xenon|xenon|131|0
Cs|xesi|caesium|133|1
La|lantan|lanthanum|139|3
Ce|xeri|cerium|140|3,4
Pr|praseođim|praseodymium|141|3
Nd|neođim|neodymium|144|3
Pm|prometi|promethium|145|3
Sm|samari|samarium|150|3,2
Eu|europi|europium|152|3,2
Gd|gađolini|gadolinium|157|3
Tb|tecbi|terbium|159|3
Dy|dysprosi|dysprosium|163|3
Ho|honmi|holmium|165|3
Er|ecbi|erbium|167|3
Tm|tuli|thulium|169|3
Yb|ytecbi|ytterbium|173|3,2
Lu|lutexi|lutetium|175|3
Hf|hafni|hafnium|178|4
Ta|tantan|tantalum|181|5
W|vonfram|tungsten|184|6
Re|reni|rhenium|186|7,4,6
Os|osmi|osmium|190|4,8
Ir|iriđi|iridium|192|4,3
Pt|bạch kim|platinum|195|2,4
Au|vàng|gold|197|3,1
Hg|thủy ngân|mercury|201|2,1
Tl|tali|thallium|204|1,3
Pb|chì|lead|207|2,4
Bi|bismut|bismuth|209|3
Po|poloni|polonium|209|2,4
At|atatin|astatine|210|1
Rn|rađon|radon|222|0
Fr|franxi|francium|223|1
Ra|rađi|radium|226|2
Ac|actini|actinium|227|3
Th|thori|thorium|232|4
Pa|protactini|protactinium|231|5,4
U|urani|uranium|238|6,4
Np|neptuni|neptunium|237|5,4,6
Pu|plutoni|plutonium|244|4,3,6
Am|amerixi|americium|243|3,4
Cm|curi|curium|247|3
Bk|beckeli|berkelium|247|3,4
Cf|californi|californium|251|3
Es|einsteini|einsteinium|252|3
Fm|fecmi|fermium|257|3
Md|mendelevi|mendelevium|258|3
No|nobeli|nobelium|259|2,3
Lr|lorenxi|lawrencium|262|3
Rf|rutherfordi|rutherfordium|267|4
Db|dubni|dubnium|268|5
Sg|seaborgi|seaborgium|271|6
Bh|bohri|bohrium|270|7
Hs|hassi|hassium|277|8
Mt|meitneri|meitnerium|278|3
Ds|darmstadti|darmstadtium|281|2
Rg|roentgeni|roentgenium|282|3
Cn|copernixi|copernicium|285|2
Nh|nihoni|nihonium|286|1,3
Fl|flerovi|flerovium|289|2,4
Mc|moscovi|moscovium|290|3,1
Lv|livermori|livermorium|293|2,4
Ts|tennessin|tennessine|294|1,3,5
Og|oganesson|oganesson|294|0
"""
EXTRA = {}
for _line in _TABLE.strip().splitlines():
    _sym, _vi, _en, _mass, _val = _line.split("|")
    EXTRA[_sym] = (_vi, _en, float(_mass) if "." in _mass else int(_mass), [int(v) for v in _val.split(",")])


def _fold(text: str) -> str:
    """Bỏ dấu, chữ thường: 'Bạch Kim' và 'bach kim' như nhau."""
    s = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def lookup(text: str):
    """Tên hoặc kí hiệu -> (kí hiệu, tên, nguyên tử khối hoặc None, [hóa trị]); không có thì None."""
    key = _fold(text)
    for sym, name in ELEMENT_NAMES.items():                        # nguyên tố đã có thẻ in sẵn
        if key in (_fold(sym), _fold(name)) and sym in VALENCE:
            return sym, name, ATOMIC_MASS.get(sym), list(VALENCE[sym])
    for sym, (name, english, mass, valence) in EXTRA.items():
        if key in (_fold(sym), _fold(name), _fold(english)):
            return sym, name, mass, list(valence)
    return None
