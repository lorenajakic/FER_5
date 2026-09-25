db.dvdrent.mapReduce(
    `function() {
        if (this.customer.address.country && this.staff.address.country) {
			let value = {};
			value[this.customer.address.country] = 1;
			emit(this.staff.address.country, value);		
		}
    }`,   
    `function(key, values) {
        var rv = values[0];
		for (let i = 1; i < values.length; ++i) {
            Object.keys(values[i]).forEach((key) => {
				let val = +values[i][key];
                if (rv[key]) {
					rv[key] += val;
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
			let arr = [];
			
			Object.keys(value).forEach((key) => {
				if (value[key] >= 10)
                    arr.push({
                        country: key + " (" + value[key] + ")",
                        count: value[key]
                    });
            });	
            arr.sort(function (a, b) {
				return (a.count == b.count) ? a.country.localeCompare(b.country) :  b.count - a.count;
            });			
            return arr.map(x => x.country);
       	}`
    }
);