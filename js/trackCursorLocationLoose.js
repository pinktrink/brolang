(function(){
    var mouseEvents = [
        'mouseenter', 'mouseover', 'mousemove', 'mousedown', 'mouseup',
        'click', 'dblclick', 'contextmenu', 'wheel', 'mouseout'
    ];

    for (var i = 0, j = mouseEvents.length; i < j; i++) {
        document.addEventListener(i, function(e) {
            window._brolang_cursor_position = [e.clientX, e.clientY];
        });
    }
})();
