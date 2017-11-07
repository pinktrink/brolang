return (function() {{
    window._brolang_error = {{
        error: false,
        exceptionType: '',
        exceptionMessage: ''
    }};
    try {{
        {}
    }} catch (e) {{
        window._brolang_error = {{
            error: true,
            exceptionType: e.constructor.name,
            exceptionMessage: e.message
        }};
        throw e;
    }}
}})();
