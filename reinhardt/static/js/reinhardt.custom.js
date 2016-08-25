/* 
    GoodCrypto custom javascript
    
    To do:
        Alert if no jQuery.

    Copyright Nothing of ours to copyright yet. 
    Last modified: 2013-11-11 
*/

/*	
   Check for jQuery.
   
   If it's missing and django.jQuery is available, use django.jQuery.
   
   If we're using Django and window.jQuery exists, 
   window.jQuery has probably been included explicitly to override django.jQuery.
*/
if (typeof jQuery === "undefined") {
    if (typeof django === "undefined" || typeof django.jQuery === "undefined") {
        alert('missing jQuery');
    }
    else {
        jQuery = django.jQuery;
        $ = jQuery;
    }
}

// Alert if jQuery is not available.
if (typeof $ === "undefined") {
    
}

// global namespace

// avoid errors when the console is not available
// http://stackoverflow.com/questions/690251/what-happened-to-console-log-in-ie8
_console_alert_fallback = false;
_console_available = (typeof console === "undefined" || typeof console.log === "undefined");
if (_console_available) {
    console = {};
    if (_console_alert_fallback) {
        console.log = function(msg) {
            alert(msg);
        };
    } else {
         console.log = function() {};
    }
}

// convenience function to log a message
log = function() {
    var msg = '';
    
    for (var i = 0; i < arguments.length; ++i) {
        
        arg = arguments[i];
        
        // if not a jQuery object
        //if ( ! (arg instanceof $) ) {
        
        // if it's an object
        if (typeof arg == "object") {
            arg = jsonify(arg);
        }
        
        if (i > 0) {
            msg += ' ';
        }
        msg += arg;
        
    }
    console.log(msg);
},	
    
// alert and log a message
log_alert = function(msg) {
    if (_console_available) {
        log(msg);
    }
    alert(msg);
},	
    
// exit with an error
fail = function() {
    throw new Error(arguments[0]);
},	

jsonify = function(arg) {
    var json;
        
    try {
        json = JSON.stringify(arg);
    }
    catch (e) {
        // for less capable browsers
        json += '{';
        
        for (var name in arg) {
            if (arg.hasOwnProperty(name)) {
                if (json.length > 1) {
                    json += ',';
                }
                json += '"' + name + '"' + ':' + arg[name];
            }
        }
    
        json += '{';
    }
    
    return json;
},

(function($){

    /* gettext() is in jquery but for some reason can't always be found */
    /*function $.gettext(txt){ return txt}*/

      
 	$.fn.extend({ 
 		
 	    /* sample jquery plugin
 		pluginname: function() {

			//Iterate over the current set of matched elements
    		return this.each(function() {
			
				//code to be inserted here
			
    		});
    	}
    	*/
            
	});
	
})(jQuery);

