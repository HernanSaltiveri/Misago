from typing import Dict, List, Tuple, Union

from ariadne import MutationType
from pydantic import EmailStr, create_model

from ...auth import create_user_token
from ...hooks import (
    create_user_hook,
    create_user_token_hook,
    register_input_hook,
    register_input_model_hook,
    register_user_hook,
)
from ...types import (
    AsyncRootValidator,
    AsyncValidator,
    GraphQLContext,
    RegisterInput,
    RegisterInputModel,
    User,
)
from ...users.create import create_user
from ...validation import (
    ErrorsList,
    passwordstr,
    usernamestr,
    validate_data,
    validate_email_is_available,
    validate_model,
    validate_username_is_available,
)


register_mutation = MutationType()


@register_mutation.field("register")
async def resolve_register(_, info, *, input):  # pylint: disable=redefined-builtin
    input_model = await register_input_model_hook.call_action(
        create_input_model, info.context
    )
    cleaned_data, errors = validate_model(input_model, input)

    if cleaned_data:
        validators = {
            "name": [validate_username_is_available(),],
            "email": [validate_email_is_available()],
        }
        cleaned_data, errors = await register_input_hook.call_action(
            validate_input_data, info.context, validators, cleaned_data, errors
        )

    if errors:
        return {"errors": errors}

    user = await register_user_hook.call_action(
        register_user, info.context, cleaned_data
    )
    token = await create_user_token_hook.call_action(
        create_user_token, info.context, user
    )

    return {"user": user, "token": token}


async def create_input_model(context: GraphQLContext) -> RegisterInputModel:
    return create_model(
        "RegisterInput",
        name=(usernamestr(context["settings"]), ...),
        email=(EmailStr, ...),
        password=(passwordstr(context["settings"]), ...),
    )


async def validate_input_data(
    context: GraphQLContext,
    validators: Dict[str, List[Union[AsyncRootValidator, AsyncValidator]]],
    cleaned_data: RegisterInput,
    errors: ErrorsList,
) -> Tuple[RegisterInput, ErrorsList]:
    errors = await validate_data(cleaned_data, validators, errors)
    return cleaned_data, errors


async def register_user(context: GraphQLContext, cleaned_data: RegisterInput) -> User:
    return await create_user_hook.call_action(
        create_user,
        cleaned_data["name"],
        cleaned_data["email"],
        password=cleaned_data["password"],
        extra={},
    )
