db.dvdrent.mapReduce(
    `function() {
		for (let c of this.film.categories) {
			let year = new Date(this.rental_date).getFullYear();
            let value = {};
            value[c.name] = {
                amount: this.payment && this.payment.amount ? this.payment.amount: 0,
                count: 1
            }
			emit(year, value);		
		}
    }`,   
    `function(key, values) {
        var rv = values[0];
		for (let i = 1; i < values.length; ++i) {
            Object.keys(values[i]).forEach((key) => {
				let val = values[i][key];
                if (rv[key]) {
					rv[key].amount += val.amount;
					rv[key].count += val.count;
				} else {
				   rv[key] = val;
				}
            });			
		}                
		return rv;
		
    }`,
    { 
    finalize: `
        function (key, value) {
			let arr = Object.keys(value).map(key => {
				return {
                    ...value[key],
                    "category": key
				}
			});
			let maxAmount = arr.reduce((a,b) => a.amount > b.amount ? a : b);
			let maxCount = arr.reduce((a,b) => a.count > b.count ? a : b);
			return {
				maxAmount: maxAmount.category + ' (' + maxAmount.amount.toFixed(3) +  ')', 
				maxCount: maxCount.category + ' (' + maxCount.count +  ')', 
			};
        }`
    }
);