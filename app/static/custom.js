$(function() {
  // validate log in form
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
  
  // validate sign up form
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
        equalTo: "[name='password']"
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

  // validate search form
  $("form[name='search']").validate({
    rules: {
      year: "digits",
      isbn: {
        rangelength: [10, 10]
      }
    },
    messages: {
      year: "Please enter a valid year",
      isbn: "Must be 10 characters long"
    },
    submitHandler: function(form) {
      form.submit();
    }
  });

  // validate review form
  $(".modal").on("shown.bs.modal", function(){
    const form = $(this).find("form[name='review']");
    const rating = $(form).find("input[type='radio']");
    const btn = $(form).find("button[type='submit']");
    $(btn).prop("disabled", true);
    rating.on("change", function () {
      $(btn).prop("disabled", rating.filter(":checked").length < 1);
    });
  });

  // reset review form on close
  $(".modal").on("hidden.bs.modal", function(){
    $(this).find("button[type='submit']").prop("disabled", true);
    $(this).find("form")[0].reset();
  });  
});
