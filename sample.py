class const():
    # API Return statuses
    HTTP_200_OK = 'HTTP_200_OK'
    HTTP_404_NOT_FOUND = 'HTTP_404_NOT_FOUND'
    HTTP_201_CREATED = 'HTTP_201_CREATED'
    HTTP_400_BAD_REQUEST = 'HTTP_400_BAD_REQUEST'
    HTTP_202_ACCEPTED = 'HTTP_202_ACCEPTED'
    HTTP_409_CONFLICT = 'HTTP_409_CONFLICT'
    HTTP_401_UNAUTHORIZED = 'HTTP_401_UNAUTHORIZED'

    # Users types
    BASIC_USER_ROLE = 100
    INSTRUCTOR_ROLE = 210
    TEACHER_ASSISTANT_ROLE = 220
    VISITING_PROFESSOR_ROLE = 230
    PROFESSOR_ROLE = 240
    LIBRARIAN_ROLE = 300

    SECRET_KEY = 'secret_key'


class UserDetailPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        user = User.get_instance(request)

        if not user:
            return False

        site_user_role = request.META['PATH_INFO'].split('/')[-1]
        if request.method == 'GET' and (user.pk == int(site_user_role) or user.role == const.LIBRARIAN_ROLE):
            result = True
        elif request.method == 'POST' and (user.pk == int(site_user_role) or user.role == const.LIBRARIAN_ROLE):
            result = True
        elif request.method == 'DELETE' and user.role == const.LIBRARIAN_ROLE:
            result = True
        elif request.method == 'PATCH':
            if user.role == const.LIBRARIAN_ROLE:
                result = True
            elif user.pk == int(site_user_role):
                result = True
                try:
                    request.data['role']
                    result = False
                except MultiValueDictKeyError:
                    pass
            else:
                result = False
        else:
            result = False

        return result


class User(AbstractUser):
    USER_TYPE_CHOICES = [(const.BASIC_USER_ROLE, 'Basic user'),
                         (const.INSTRUCTOR_ROLE, 'Instructor'),
                         (const.TEACHER_ASSISTANT_ROLE, 'Teacher Assistant'),
                         (const.VISITING_PROFESSOR_ROLE, 'Visiting Professor'),
                         (const.PROFESSOR_ROLE, 'Professor'),
                         (const.LIBRARIAN_ROLE, 'Librarian')]

    role = models.IntegerField(default=const.BASIC_USER_ROLE, choices=USER_TYPE_CHOICES)
    address = models.CharField(max_length=100, default='innopolis')
    phone = models.DecimalField(unique=True, default=0, max_digits=11, decimal_places=0)
    telegram_id = models.IntegerField(default=0)

    @staticmethod
    def get_instance(request):
        """
        Method to recognize user by his request

        :param request: API request
        :return: user instance if such exist, None otherwise
        """
        if 'HTTP_HOST' in request.META:
            try:
                token = re.split(' ', request.META['HTTP_BEARER'])[1]
                payload = jwt.decode(token, const.SECRET_KEY)
                email = payload['email']
                user_id = payload['user_id']

                user = User.objects.get(
                    email=email,
                    id=user_id
                )

            except jwt.ExpiredSignature or jwt.DecodeError or jwt.InvalidTokenError:
                return None
            except User.DoesNotExist:
                return None
            except KeyError:
                return None
            # empty session catcher
            except jwt.DecodeError:
                return None

            return user
        else:
            return None


"""
    ------------------------------------
    Classes to handel user serialization
    ------------------------------------
"""


class UserDetailSerializer(serializers.ModelSerializer):
    orders = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id',
                  'email',
                  'role',
                  'first_name',
                  'last_name',
                  'address',
                  'phone',
                  'username',
                  'orders',
                  'telegram_id')


"""
    -----------------------------------
    Classes to handel user API requests
    -----------------------------------
"""


class UserDetail(APIView):
    """
        Class to get one User by id
    """
    permission_classes = (UserDetailPermission,)

    @staticmethod
    def get(request, user_id):
        """
            GET request to get one particular user
            :param request:
            :param user_id
            :return: HTTP_200_OK and JSON-Documents: if all good
                    HTTP_404_NOT_FOUND: if user don`t exist
        """
        result = {'status': '', 'data': {}}

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            result['status'] = const.HTTP_404_NOT_FOUND
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        serializer = UserDetailSerializer(user)
        result['data'] = serializer.data
        result['status'] = const.HTTP_200_OK
        return Response(result, status=status.HTTP_200_OK)

    @staticmethod
    def patch(request, user_id):
        """
            PATCH request to update users
            :param request:
            :param user_id:
            :return: HTTP_202_ACCEPTED and JSON-Document: update is success
                     HTTP_400_BAD_REQUEST and JSON-Document with errors: data is not valid
                     HTTP_404_NOT_FOUND: user with such id is not found
        """

        result = {'status': '', 'data': {}}

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            result['status'] = const.HTTP_404_NOT_FOUND
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        serializer = UserDetailSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            # First, need to check whether the user try to change his role
            # We return 'accepted' in case that 'hacker' who try to change state
            # Might try several times before he totally burn in tears about our security :)
            # NOTE: User.get_instance(request).role - the instance of requester
            if User.get_instance(request).role != const.LIBRARIAN_ROLE:
                return Response(result, status=status.HTTP_202_ACCEPTED)
            # If pass, then save all
            serializer.save()
            result['status'] = const.HTTP_202_ACCEPTED
            return Response(result, status=status.HTTP_202_ACCEPTED)

        result['status'] = const.HTTP_400_BAD_REQUEST
        result['data'] = serializer.errors

        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def delete(request, user_id):
        """
        DELETE request: delete one particular user by ID
        :param request:
        :return: HTTP_200_OK: if user was deleted success
                 HTTP_404_NOT_FOUND: if user with such id not found
                 HTTP_400_BAD_REQUEST: if wrong format of input data
        """

        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({'status': const.HTTP_404_NOT_FOUND, 'data': {}}, status=status.HTTP_404_NOT_FOUND)
            serializer = UserDetailSerializer(user)
            user.delete()
            return Response({'status': const.HTTP_200_OK, 'data': serializer.data})
        else:
            return Response({'status': const.HTTP_400_BAD_REQUEST, 'data': {}}, status=status.HTTP_400_BAD_REQUEST)





