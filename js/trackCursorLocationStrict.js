(function(){
    var mouseEvents = [
        'mouseenter', 'mouseover', 'mousemove', 'mousedown', 'mouseup',
        'click', 'dblclick', 'contextmenu', 'wheel', 'mouseout'
    ];

    for (var i = 0, j = mouseEvents.length; i < j; i++) {
        var allElements = document.querySelectorAll('*');

        for (var k = 0, l = allElements.length; k < l; k++) {
            allElements[k].addEventListener(i, function(e) {
                window._brolang_cursor_position = [e.clientX, e.clientY];
                e.preventDefault();
                e.stopPropagation();
            });
        }
    }
})();
