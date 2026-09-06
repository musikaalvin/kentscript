:: email - SMTP/IMAP email client
::
:: Usage:
::   import email;
::   email.send("smtp.gmail.com", 587, "user@gmail.com", "app-password",
::              "from@gmail.com", ["to@example.com"], "Subject", "Body");
::
::   let msgs = email.fetch("imap.gmail.com", "user@gmail.com", "password",
::                          mailbox: "INBOX", limit: 5);
::   for m in msgs { print(m["subject"]); }

func send(host, port, user, password, from_addr, to_addrs, subject, body, use_tls) {
    if use_tls == none { use_tls = true; }
    return system_smtp_send(host, port, user, password, from_addr, to_addrs, subject, body, use_tls);
}

func send_html(host, port, user, password, from_addr, to_addrs, subject, html_body, use_tls) {
    if use_tls == none { use_tls = true; }
    return system_smtp_send_html(host, port, user, password, from_addr, to_addrs, subject, html_body, use_tls);
}

func fetch(host, user, password, mailbox, limit, ssl) {
    if mailbox == none { mailbox = "INBOX"; }
    if limit == none { limit = 10; }
    if ssl == none { ssl = true; }
    let result = system_imap_fetch(host, user, password, mailbox, limit, ssl);
    if result["success"] {
        return result["messages"];
    }
    println("email error: " + result["error"]);
    return [];
}

export { send, send_html, fetch };
