import os
import pytest
from email_system import (
    Email,
    EmailAddress,
    EmailService,
    LoggingEmailService,
    Status,
)


class TestEmailAddress:
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


class TestEmailPrepare:
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
            sender=None,  # Отсутствует отправитель
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


class TestEmailService:
    def test_should_return_failed_when_email_invalid(self):
        email = Email(
            subject="",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=[EmailAddress("you@you.com")],
        )
        email.prepare()  # INVALID

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


class TestLoggingEmailService:
    LOGFILE = "email_send.log"

    def setup_method(self):
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
