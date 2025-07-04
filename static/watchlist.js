function fetchData() {
    var watchquery = "{{ query|escapejs }}";  // Safer template interpolation

    if (watchquery !== "") {
        fetch(`/api/watchlist/${watchquery}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                var currentPriceElement = document.getElementById('currentPrice');
                var changepercentage = document.getElementById('changePercentage');
                var form = document.getElementById('updatestocksform');

                if (currentPriceElement) {
                    var stocks = data.stocks;
                    if (stocks && stocks.length > 0) {
                        var currentPrice = stocks[0][1];
                        currentPriceElement.textContent = "Current Price: $" + currentPrice;

                        var changeper = stocks[0][2];
                        var market = stocks[0][4];
                        document.getElementById("marketstatus").innerHTML = market;

                        if (changeper > 0) {
                            changepercentage.classList.add('dark:text-green-500');
                        } else {
                            changepercentage.classList.add('dark:text-red-500');
                        }

                        changepercentage.textContent = changeper + " %";
                        document.getElementById("currentprice").value = currentPrice;
                        console.log(`Current Price: ${currentPrice}`);
                    }
                }
            })
            .catch(error => {
                console.error('There was a problem with the fetch operation:', error);
            });
    }
}

fetchData();
setInterval(fetchData, 5000);
