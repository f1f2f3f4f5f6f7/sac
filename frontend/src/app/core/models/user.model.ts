import { Role } from "./role.enum"

export interface User {
    id: number,
    codigo: string,
    nombre: string,
    email: string,
    password: string,
    rol: Role,
    escuela: number,
    activo: boolean,
}

export type UserLogin = Omit<User, 'id' | 'nombre' | 'nombre' | 'email' | 'rol' | 'escuela' | 'activo'>

export type UserWithToken = Omit<User, 'password'> & { token: string }