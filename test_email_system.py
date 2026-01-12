import os
import pytest
from email_system import (
    Email,
    EmailAddress,
    EmailService,
    LoggingEmailService,
    Status,
)


class TestEmailSystem:

    def test_should_mask_email(self):
        addr = EmailAddress("alexander@example.com")
        assert addr.masked == "al***@example.com"

    def test_invalid_email_format(self):
        with pytest.raises(ValueError):
            EmailAddress("invalid_email")

    def test_should_normalize_address(self):
        addr = EmailAddress("  UsEr@Example.COM  ")
        assert addr.value == "user@example.com"

    def test_should_fail_on_invalid_domain(self):
        with pytest.raises(ValueError):
            EmailAddress("user@example.xyz")

    def test_invalid_email_no_at_symbol(self):
        with pytest.raises(ValueError):
            EmailAddress("invalid-email.com")

    def test_invalid_email_wrong_tld(self):
        with pytest.raises(ValueError):
            EmailAddress("user@test.org")

    def test_valid_email_com(self):
        addr = EmailAddress("test@example.com")
        assert str(addr) == "test@example.com"

    def test_valid_email_ru(self):
        addr = EmailAddress("test@example.ru")
        assert str(addr) == "test@example.ru"

    def test_valid_email_net(self):
        addr = EmailAddress("test@example.net")
        assert str(addr) == "test@example.net"

    def test_email_masked_format(self):
        addr = EmailAddress("longname@example.com")
        assert addr.masked == "lo***@example.com"

    def test_email_masked_short_name(self):
        addr = EmailAddress("ab@example.com")
        assert addr.masked == "ab***@example.com"

    def test_special_chars_in_email_address(self):
        addr = EmailAddress("user+tag@test.com")
        assert addr.masked == "us***@test.com"

    def test_invalid_email_empty_string(self):
        with pytest.raises(ValueError):
            EmailAddress("")

    def test_invalid_email_only_at(self):
        with pytest.raises(ValueError):
            EmailAddress("@test.com")

    def test_invalid_email_no_domain(self):
        with pytest.raises(ValueError):
            EmailAddress("user@")

    def test_invalid_email_no_local(self):
        with pytest.raises(ValueError):
            EmailAddress("@test.com")

    # --- Email prepare tests ---
    def test_should_mark_invalid_when_no_subject(self):
        email = Email(
            subject="",
            body="Body",
            sender=EmailAddress("a@a.com"),
            recipients=[EmailAddress("b@b.com")],
        )
        email.prepare()
        assert email.status == Status.INVALID

    def test_should_mark_invalid_when_no_sender(self):
        email = Email(
            subject="Valid Subject",
            body="Body",
            sender=None,
            recipients=[EmailAddress("b@b.com")],
        )
        email.prepare()
        assert email.status == Status.INVALID

    def test_should_clean_up_subject_and_body(self):
        email = Email(
            subject=" Hi ",
            body=" Test Body ",
            sender=EmailAddress("a@a.com"),
            recipients=[EmailAddress("b@b.com")],
        )
        email.prepare()
        assert email.subject == "Hi"
        assert email.body == "Test Body"
        assert email.status == Status.READY
        assert email.short_body == "Test Body"

    def test_prepare_sets_ready_status(self):
        email = Email(
            subject="Test",
            body="Body",
            sender=EmailAddress("from@test.com"),
            recipients=[EmailAddress("to@test.com")]
        )
        email.prepare()
        assert email.status == Status.READY

    def test_prepare_sets_invalid_on_empty_subject(self):
        email = Email("", "Body", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        assert email.status == Status.INVALID

    def test_prepare_sets_invalid_on_empty_body(self):
        email = Email("Subj", "", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        assert email.status == Status.INVALID

    def test_prepare_sets_invalid_on_empty_sender(self):
        email = Email("Subj", "Body", None, [EmailAddress("t@test.com")])
        email.prepare()
        assert email.status == Status.INVALID

    def test_prepare_sets_invalid_on_empty_recipients(self):
        email = Email("Subj", "Body", EmailAddress("f@test.com"), [])
        email.prepare()
        assert email.status == Status.INVALID

    def test_email_with_whitespace_in_fields(self):
        email = Email("  Test  ", "  Body  ", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        assert email.subject == "Test"
        assert email.body == "Body"
        assert email.status == Status.READY

    def test_non_ascii_in_email(self):
        email = Email("Тема", "Текст", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        assert email.status == Status.READY

    def test_add_short_body_truncates(self):
        email = Email("S", "A" * 100, EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.add_short_body()
        assert email.short_body == "A" * 20 + "..."

    def test_add_short_body_no_truncate(self):
        email = Email("S", "Short", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.add_short_body()
        assert email.short_body == "Short"

    def test_short_body_default_length(self):
        long_body = "x" * 60
        email = Email("S", long_body, EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.add_short_body()
        assert len(email.short_body) == 23  # 20 + ...

    def test_email_short_body_with_newlines(self):
        body = "Line1\nLine2\nLine3"
        email = Email("S", body, EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.add_short_body(10)
        assert email.short_body == "Line1 Line..."

    # --- EmailService tests ---
    def test_should_return_failed_when_email_invalid(self):
        email = Email(
            subject="",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=[EmailAddress("you@you.com")],
        )
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert result[0].status == Status.FAILED

    def test_send_creates_individual_emails_for_each_recipient(self):
        email = Email(
            subject="Subject",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=[EmailAddress("a@a.com"), EmailAddress("b@b.com")],
        )
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert len(result) == 2
        assert result[0].recipients[0].value == "a@a.com"
        assert result[1].recipients[0].value == "b@b.com"

    def test_send_should_mark_as_sent(self):
        email = Email(
            subject="Subject",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=[EmailAddress("you@you.com")],
        )
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert result[0].status == Status.SENT

    def test_should_not_change_original_email(self):
        email = Email(
            subject="Subject",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=[EmailAddress("you@you.com")],
        )
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert email.date is None
        assert email.status == Status.READY
        assert result[0].date is not None

    def test_send_ready_email_creates_copies(self):
        email = Email("S", "B", EmailAddress("f@test.com"), [EmailAddress("t1@test.com"), EmailAddress("t2@test.com")])
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert len(result) == 2
        assert all(e.status == Status.SENT for e in result)
        assert email.status == Status.READY

    def test_send_draft_email_fails(self):
        email = Email("S", "B", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        service = EmailService()
        result = service.send_email(email)
        assert result[0].status == Status.FAILED
        assert email.status == Status.DRAFT

    def test_send_invalid_email_fails(self):
        email = Email("", "", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert result[0].status == Status.FAILED

    def test_original_email_not_modified_after_send(self):
        email = Email("S", "B", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        original_status = email.status
        service = EmailService()
        result = service.send_email(email)
        assert email.status == original_status

    def test_multiple_recipients(self):
        recips = [EmailAddress(f"user{i}@test.com") for i in range(5)]
        email = Email("S", "B", EmailAddress("f@test.com"), recips)
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert len(result) == 5

    def test_email_date_is_set_on_send(self):
        email = Email("S", "B", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        service = EmailService()
        result = service.send_email(email)
        assert result[0].date is not None

    def test_email_initial_date_is_none(self):
        email = Email("S", "B", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        assert email.date is None

    def test_email_recipients_always_list(self):
        email = Email("S", "B", EmailAddress("f@test.com"), EmailAddress("t@test.com"))
        assert isinstance(email.recipients, list)
        assert len(email.recipients) == 1

    def test_send_to_empty_recipients_list(self):
        email = Email("S", "B", EmailAddress("f@test.com"), [])
        email.status = Status.READY
        service = EmailService()
        result = service.send_email(email)
        assert result == []

    def test_send_email_does_not_modify_recipients(self):
        recips = [EmailAddress("a@test.com")]
        email = Email("S", "B", EmailAddress("f@test.com"), recips)
        recips.append(EmailAddress("b@test.com"))
        assert len(email.recipients) == 1

    def test_email_with_same_sender_and_recipient(self):
        addr = EmailAddress("user@test.com")
        email = Email("S", "B", addr, addr)
        email.prepare()
        assert email.status == Status.READY

    def test_email_repr_uses_masked_sender(self):
        email = Email("S", "B", EmailAddress("sender@test.com"), [EmailAddress("r@test.com")])
        repr_str = repr(email)
        assert "se***@test.com" in repr_str

    def test_email_repr_with_multiple_recipients(self):
        email = Email("S", "B", EmailAddress("f@test.com"), [
            EmailAddress("r1@test.com"),
            EmailAddress("r2@test.com")
        ])
        repr_str = repr(email)
        assert "r1@test.com" in repr_str
        assert "r2@test.com" in repr_str

    # --- LoggingEmailService tests ---
    LOGFILE = "email_send.log"

    def setup_method(self):
        if os.path.exists(self.LOGFILE):
            os.remove(self.LOGFILE)

    def teardown_method(self):
        if os.path.exists(self.LOGFILE):
            os.remove(self.LOGFILE)

    def test_should_create_log_file_and_log_data(self):
        email = Email(
            subject="Hello",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=[EmailAddress("you@you.com")],
        )
        email.prepare()
        service = LoggingEmailService()
        service.send_email(email)
        assert os.path.exists(self.LOGFILE)
        with open(self.LOGFILE, "r", encoding="utf-8") as file:
            content = file.read()
            assert "FROM me***@me.com" in content
            assert "TO yo***@you.com" in content
            assert "STATUS=sent" in content

    def test_logging_service_writes_to_file(self):
        email = Email("Test", "Body", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        service = LoggingEmailService()
        service.send_email(email)
        assert os.path.exists(self.LOGFILE)
        with open(self.LOGFILE, encoding="utf-8") as f:
            content = f.read()
            assert "sent" in content.lower()

    def test_logging_service_logs_failed_emails(self):
        email = Email("", "", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        service = LoggingEmailService()
        service.send_email(email)
        with open(self.LOGFILE, encoding="utf-8") as f:
            content = f.read()
            assert "failed" in content.lower()

    def test_logging_service_appends_to_existing_log(self):
        with open(self.LOGFILE, "w", encoding="utf-8") as f:
            f.write("Initial\n")
        email = Email("Test", "Body", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        service = LoggingEmailService()
        service.send_email(email)
        with open(self.LOGFILE, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) >= 2
            assert any("sent" in line.lower() for line in lines)

    def test_logging_service_handles_unicode(self):
        email = Email("Тема", "Текст", EmailAddress("f@test.com"), [EmailAddress("t@test.com")])
        email.prepare()
        service = LoggingEmailService()
        service.send_email(email)
        assert os.path.exists(self.LOGFILE)