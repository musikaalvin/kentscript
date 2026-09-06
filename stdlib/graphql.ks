:: graphql - GraphQL client
::
:: Usage:
::   import graphql;
::   let gql = graphql.Client("https://api.example.com/graphql");
::   let r = gql.query("{ users { name } }");
::   print(r);

class Client {
    func __init__(self, url, headers) {
        if headers == none { headers = {}; }
        self.url = url;
        self.headers = headers;
    }

    func query(self, query, variables) {
        if variables == none { variables = {}; }
        let body = {"query": query, "variables": variables};
        let all_headers = {"Content-Type": "application/json"};
        let all_headers = self._merge(all_headers, self.headers);
        return system_http_post(self.url, system_json_dumps(body), all_headers);
    }

    func mutate(self, mutation, variables) {
        if variables == none { variables = {}; }
        let body = {"query": mutation, "variables": variables};
        let all_headers = {"Content-Type": "application/json"};
        let all_headers = self._merge(all_headers, self.headers);
        return system_http_post(self.url, system_json_dumps(body), all_headers);
    }

    func _merge(self, a, b) {
        let result = {};
        let ka = a.keys();
        for i in range(len(ka)) { result[ka[i]] = a[ka[i]]; }
        let kb = b.keys();
        for i in range(len(kb)) { result[kb[i]] = b[kb[i]]; }
        return result;
    }
}

export { Client };
