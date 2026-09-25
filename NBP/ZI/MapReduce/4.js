db.nobelprizes.mapReduce(
    `function() {
        var self = this;
		if (this.year >=1900 && this.year < 2000) {
			var decade = this.year - this.year % 10;
    		let value = {};
            value[this.category] = this.laureates.length;
            emit(decade, value);
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
			let sum = 0, cnt = 0, min = 100000, max = 0;
			Object.keys(value).forEach(key => {                
	            if (value[key] > max) max = value[key];
                if (value[key] < min) min = value[key];
            });             
            let top = [];
            Object.keys(value).forEach(key => {                
	            if (value[key] == max) top.push(key);
            }); 
            top.sort();
            value.top = top;
            return {               
               min, max, top
            }
       	}`
    }
);
