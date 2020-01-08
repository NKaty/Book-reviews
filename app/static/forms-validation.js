$(function() {
  $("form[name='login']").validate({
    rules: {
      username: "required",
      password: "required"
    },
    messages: {
      username: "Please enter your username",
      password: "Please enter your password"
    },
    submitHandler: function(form) {
      form.submit();
    }
  });
  
  $("form[name='signup']").validate({
    rules: {
      username: {
        required: true,
        minlength: 2
      },
      password: {
        required: true,
        minlength: 6
      },
      "conf-password": {
        required: true,
        equalTo: '[name="password"]'
      }
    },
    messages: {
      username: {
        required: "Please enter your username",
        minlength: "Must be at least 2 characters long"
      },
      password: {
        required: "Please enter your password",
        minlength: "Must be at least 6 characters long"
      },
      "conf-password": {
        required: "Please confirm your password",
        equalTo: "Passwords must match"
      }
    },
    submitHandler: function(form) {
      form.submit();
    }
  });
});
