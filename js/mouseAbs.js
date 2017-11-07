function uuid() {{
    return 'bro-xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    }});
}}

if (!window._brolang_abs_el) {{
    window._brolang_abs_el = document.createElement('div');

    window._brolang_abs_el.style.position = 'fixed';
    window._brolang_abs_el.style.width = 0;
    window._brolang_abs_el.style.height = 0;
    window._brolang_abs_el.style.top = '{0}px';
    window._brolang_abs_el.style.left = '{1}px';
    window._brolang_abs_el.id = uuid();
    document.body.appendChild(window._brolang_abs_el);

    return window._brolang_abs_el.id;
}}

window._brolang_abs_el.style.top = '{0}px';
window._brolang_abs_el.style.left = '{1}px';

return window._brolang_abs_el.id;
