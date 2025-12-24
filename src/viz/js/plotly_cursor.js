(function() {
    const plot = document.querySelector('.plotly-graph-div');
    if (!plot) return;

    let cursorA = null;
    let cursorB = null;
    const STEP_SEC = 0.05;

    function snapX(x) {
        const xs = plot.data[0].x;
        let best = xs[0], min = Math.abs(xs[0] - x);
        for (let i = 1; i < xs.length; i++) {
            const d = Math.abs(xs[i] - x);
            if (d < min) { min = d; best = xs[i]; }
        }
        return best;
    }

    function update() {
        const shapes = [];
        if (cursorA !== null) {
            shapes.push({
                type: 'line',
                x0: cursorA, x1: cursorA,
                y0: 0, y1: 1,
                xref: 'x', yref: 'paper',
                line: { color: '#d9480f', width: 2 }
            });
        }
        if (cursorB !== null) {
            shapes.push({
                type: 'line',
                x0: cursorB, x1: cursorB,
                y0: 0, y1: 1,
                xref: 'x', yref: 'paper',
                line: { color: '#1971c2', width: 2, dash: 'dot' }
            });
        }

        const ann = [];
        if (cursorA !== null && cursorB !== null) {
            ann.push({
                x: 0.5, y: 1.06,
                xref: 'paper', yref: 'paper',
                text: `Δt = ${(cursorB - cursorA).toFixed(3)} s`,
                showarrow: false
            });
        }

        Plotly.relayout(plot, { shapes: shapes, annotations: ann });
    }

    plot.on('plotly_click', function(evt) {
        const x = snapX(evt.points[0].x);
        if (evt.event.shiftKey) cursorB = x;
        else { cursorA = x; cursorB = null; }
        update();
    });

    document.addEventListener('keydown', function(e) {
        if (cursorA === null) return;
        if (e.key === 'ArrowLeft') cursorA -= STEP_SEC;
        if (e.key === 'ArrowRight') cursorA += STEP_SEC;
        cursorA = snapX(cursorA);
        update();
    });
})();
