:: template - Template engine for text generation
:: Supports variable substitution, loops, conditionals

class Template {
    func __init__(self, template_string) {
        self.template = template_string;
    }
    
    func render(self, context) {
        let result = self.template;
        
        :: Replace variables {{ var }}
        result = self._replace_variables(result, context);
        
        :: Process loops {% for %}
        result = self._process_loops(result, context);
        
        :: Process conditionals {% if %}
        result = self._process_conditionals(result, context);
        
        :: Process includes {% include %}
        result = self._process_includes(result, context);
        
        return result;
    }
    
    func _replace_variables(self, text, context) {
        let result = text;
        
        :: Find all {{ variable }} patterns
        let pattern = "{{";
        let i = 0;
        
        while i < result.length {
            let start = result.indexOf(pattern, i);
            if start == -1 { break; }
            
            let end = result.indexOf("}}", start);
            if end == -1 { break; }
            
            let var_name = result.substring(start + 2, end).trim();
            let value = self._get_value(context, var_name);
            
            result = result.substring(0, start) + str(value) + result.substring(end + 2);
            i = start + str(value).length;
        }
        
        return result;
    }
    
    func _process_loops(self, text, context) {
        let result = text;
        
        while true {
            let for_start = result.indexOf("{% for ");
            if for_start == -1 { break; }
            
            let for_end = result.indexOf("%}", for_start);
            let endfor = result.indexOf("{% endfor %}", for_end);
            
            if for_end == -1 || endfor == -1 { break; }
            
            :: Parse for statement
            let for_stmt = result.substring(for_start + 7, for_end).trim();
            let parts = for_stmt.split(" in ");
            let var_name = parts[0].trim();
            let iterable_name = parts[1].trim();
            
            :: Get iterable from context
            let iterable = self._get_value(context, iterable_name);
            
            :: Get loop body
            let body = result.substring(for_end + 2, endfor);
            
            :: Render loop
            let loop_result = "";
            for item in iterable {
                let loop_context = {...context};
                loop_context[var_name] = item;
                loop_result = loop_result + self._replace_variables(body, loop_context);
            }
            
            result = result.substring(0, for_start) + loop_result + result.substring(endfor + 13);
        }
        
        return result;
    }
    
    func _process_conditionals(self, text, context) {
        let result = text;
        
        while true {
            let if_start = result.indexOf("{% if ");
            if if_start == -1 { break; }
            
            let if_end = result.indexOf("%}", if_start);
            let endif = result.indexOf("{% endif %}", if_end);
            
            if if_end == -1 || endif == -1 { break; }
            
            :: Parse if statement
            let condition = result.substring(if_start + 6, if_end).trim();
            
            :: Check for else
            let else_pos = result.indexOf("{% else %}", if_end);
            let has_else = else_pos != -1 && else_pos < endif;
            
            :: Evaluate condition
            let is_true = self._evaluate_condition(condition, context);
            
            let body;
            if has_else {
                if is_true {
                    body = result.substring(if_end + 2, else_pos);
                } else {
                    body = result.substring(else_pos + 10, endif);
                }
            } else {
                body = is_true ? result.substring(if_end + 2, endif) : "";
            }
            
            result = result.substring(0, if_start) + body + result.substring(endif + 11);
        }
        
        return result;
    }
    
    func _process_includes(self, text, context) {
        let result = text;
        
        while true {
            let inc_start = result.indexOf("{% include ");
            if inc_start == -1 { break; }
            
            let inc_end = result.indexOf("%}", inc_start);
            if inc_end == -1 { break; }
            
            let filename = result.substring(inc_start + 11, inc_end).trim();
            filename = filename.replace('"', '').replace("'", '');
            
            :: Load and render included template
            let included = file_read_all(filename);
            let tmpl = Template(included);
            let rendered = tmpl.render(context);
            
            result = result.substring(0, inc_start) + rendered + result.substring(inc_end + 2);
        }
        
        return result;
    }
    
    func _get_value(self, context, path) {
        let parts = path.split(".");
        let value = context;
        
        for part in parts {
            if value == none { return ""; }
            value = value[part];
        }
        
        return value != none ? value : "";
    }
    
    func _evaluate_condition(self, condition, context) {
        :: Simple condition evaluation
        if condition.indexOf("==") != -1 {
            let parts = condition.split("==");
            let left = self._get_value(context, parts[0].trim());
            let right = parts[1].trim().replace('"', '').replace("'", '');
            return str(left) == right;
        } else if condition.indexOf("!=") != -1 {
            let parts = condition.split("!=");
            let left = self._get_value(context, parts[0].trim());
            let right = parts[1].trim().replace('"', '').replace("'", '');
            return str(left) != right;
        } else {
            :: Just check if variable is truthy
            let value = self._get_value(context, condition);
            return value != none && value != false && value != 0 && value != "";
        }
    }
}

func render(template_string, context) {
    let tmpl = Template(template_string);
    return tmpl.render(context);
}

func render_file(filename, context) {
    let template_string = file_read_all(filename);
    return render(template_string, context);
}

:: Filters
class TemplateFilters {
    func upper(value) {
        return str(value).toUpperCase();
    }
    
    func lower(value) {
        return str(value).toLowerCase();
    }
    
    func capitalize(value) {
        let s = str(value);
        return s.length > 0 ? s[0].toUpperCase() + s.substring(1).toLowerCase() : s;
    }
    
    func title(value) {
        return str(value).split(" ").map((w) => w[0].toUpperCase() + w.substring(1).toLowerCase()).join(" ");
    }
    
    func length(value) {
        return value.length;
    }
    
    func reverse(value) {
        if typeof(value) == "string" {
            return value.split("").reverse().join("");
        }
        return [...value].reverse();
    }
    
    func join(value, separator) {
        return value.join(separator != none ? separator : ", ");
    }
    
    func default(value, default_value) {
        return value != none && value != "" ? value : default_value;
    }
}

:: Runtime interface
func file_read_all(filename) { return system_file_read_all(filename); }

export {
    Template, render, render_file, TemplateFilters
};
