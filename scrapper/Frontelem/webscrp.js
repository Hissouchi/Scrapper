document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('scraper-form');
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const urls = document.getElementById('urls').value.split(',');
        const contentType = Array.from(document.querySelectorAll('input[name="content_type"]:checked')).map(el => el.value);
        const isFullWebsite = document.getElementById('full_website').checked;

        const response = await fetch('http://<your_django_server>/api/scrapper/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                urls,
                content_type: contentType,
                full_website: isFullWebsite,
            }),
        });

        const result = await response.json();
        if (response.ok) {
            document.getElementById('result').innerText = JSON.stringify(result, null, 2);
        } else {
            document.getElementById('result').innerText = 'Une erreur est survenue : ' + JSON.stringify(result);
        }
    });
});
