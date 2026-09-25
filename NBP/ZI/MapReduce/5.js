db.nobelprizes.mapReduce(
    `function() {
        var self = this;
		if (this.year >=1900 && this.year < 2000) {
			var decade = this.year - this.year % 10;
    		let value = {};
            value[decade] = this.laureates.length;
            emit(this.category, value);
		}
		
    }`,   
    `function(key, values) {
        var rv = {};
        values.forEach( function(value) {
			Object.keys(value).forEach(key => {
                if (rv[key]) {
                    rv[key] += value[key];
                } else {
                    rv[key] = value[key];
                }                  
            }); 			          
        });
        return rv;  
    }`,   
    { 
        finalize: `
		function (key, value) {
			let sum = 0, cnt = 0;
			Object.keys(value).forEach(key => {
                sum += value[key];
				++cnt;
            }); 
            value.avg = sum / cnt;
            return value;
       	}`
    }
);
